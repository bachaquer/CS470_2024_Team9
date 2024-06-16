import os
import openai
import json
import random
import argparse
import tqdm
import sys
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--start", required=True, type=int)
parser.add_argument("--model", default='gpt-3.5-turbo', type=str)
parser.add_argument("--end", required=True, type=int)
parser.add_argument("--dry_run", default=False, action="store_true",
    help="whether it's a dry run or real run.")
parser.add_argument(
    "--temperature", type=float, default=0.7,
    help="temperature of 0 implies greedy sampling.")


demonstration_prompt = """
Read the following table regarding "Shagun Sharma" to answer the given question.

Year | Title | Role | Channel
2015 | Kuch Toh Hai Tere Mere Darmiyaan | Sanjana Kapoor | Star Plus
2016 | Kuch Rang Pyar Ke Aise Bhi | Khushi | Sony TV
2016 | Gangaa | Aashi Jhaa | &TV
2017 | Iss Pyaar Ko Kya Naam Doon 3 | Meghna Narayan Vashishth | Star Plus
2017–18 | Tu Aashiqui | Richa Dhanrajgir | Colors TV
2019 | Laal Ishq | Pernia | &TV
2019 | Vikram Betaal Ki Rahasya Gatha | Rukmani/Kashi | &TV
2019 | Shaadi Ke Siyape | Dua | &TV

Question: What TV shows was Shagun Sharma seen in 2019?
Answer: In 2019, Shagun Sharma played in the roles as Pernia in Laal Ishq, Vikram Betaal Ki Rahasya Gatha as Rukmani/Kashi and Shaadi Ke Siyape as Dua.
"""

demonstration_prompt_row = """
Read the following table regarding "Shagun Sharma" to answer the given question.

Year | 2015 | 2016 | 2016 | 2017 | 2017-18 | 2019 | 2019 | 2019
Title | Kuch Toh Hai Tere Mere Darmiyaan | Kuch Rang Pyar Ke Aise Bhi | Gangaa | Iss Pyaar Ko Kya Naam Doon 3 | Tu Aashiqui | Laal Ishq | Vikram Betaal Ki Rahasya Gatha | Shaadi Ke Siyape
Role | Sanjana Kapoor | Khushi | Aashi Jhaa | Meghna Narayan Vashishth | Richa Dhanrajgir | Pernia | Rukmani/Kashi | Dua
Channel | Star Plus | Sony TV | &TV | Star Plus | Colors TV | &TV | &TV | &TV

Question: What TV shows was Shagun Sharma seen in 2019?
Answer: In 2019, Shagun Sharma played in the roles as Pernia in Laal Ishq, Vikram Betaal Ki Rahasya Gatha as Rukmani/Kashi and Shaadi Ke Siyape as Dua.
"""


demonstration_columns = """
Read the following table regarding "Shagun Sharma" to choose relevant columns for the following question.

Year | Title | Role | Channel
2015 | Kuch Toh Hai Tere Mere Darmiyaan | Sanjana Kapoor | Star Plus

Question: What TV shows was Shagun Sharma seen in 2019?
Relevant Columns: Year | Title | Role
"""

demonstration_rows = """
Read the following table regarding "Shagun Sharma" to choose relevant titles for the following question.

Year | 2015
Title | Kuch Toh Hai Tere Mere Darmiyaan
Role | Sanjana Kapoor
Channel | Star Plus

Question: What TV shows was Shagun Sharma seen in 2019?
Relevant Titles: Year | Title | Role
"""

prompt_row_or_column = """
Question: Which of the following options is more likely to include the names of the columns in the table?
1. Rank | Cyclist | Team | Time | UCI ProTour Points
2. Rank | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10
Answer: 1

Question: Which of the following options is more likely to include the names of the columns in the table?
1. Description Losses | 1939/40 | 1940/41 | 1941/42 | 1942/43 | 1943/44 | 1944/45 | Total
2. Description Losses | Direct War Losses | Murdered | Deaths In Prisons & Camps | Deaths Outside of Prisons & Camps | Murdered in Eastern Regions | Deaths other countries | Total
Answer: 2

Question: Which of the following options is more likely to include the names of the columns in the table?
"""

def decompose_table(table_original, columns):
    table = table_original.strip().strip('\n').strip('\n').split('\n')
    first_row = table[0].strip().split(" | ")
    cols = columns.split(" | ")
    indexes = []
    ans_table = []
    for ind in range(len(first_row)):
        if (first_row[ind] in cols):
            indexes.append(ind)
    for l in range(len(table)):
        line = table[l].strip().split(" | ")
        if (len(line) < len(first_row)):
            for i in range(len(first_row) - len(line)):
                line.append("")
        
        processed_row = []
        for ind in indexes:
            processed_row.append(line[ind])
        ans_table.append(" | ".join(processed_row))
    return '\n'.join(ans_table) + '\n'

def get_two_columns(table_original):
    table = table_original.strip().strip('\n').strip('\n').split('\n')
    two_col_table = []
    for l in range(len(table)):
        line = table[l].strip().split(" | ")
        two_col_table.append(line[0] + " | " + line[1])
    return "\n".join(two_col_table)

def decompose_table_byrows(table_original, rows):
    table = table_original.strip().strip('\n').strip('\n').split('\n')
    row = rows.split(" | ")
    ans_table = []
    for l in range(len(table)):
        line = table[l].strip().split(" | ")
        if (line[0] in row): 
            ans_table.append(table[l])
    return '\n'.join(ans_table) + '\n'


if __name__ == "__main__":
    args = parser.parse_args()

    # openai.api_key = os.getenv('OPENAI_API_KEY')
    openai.api_key = ""

    with open(f'test_qa.json') as f:
        fetaqa = json.load(f)

    now = datetime.now() 
    dt_string = now.strftime("%d_%H_%M")

    keys = list(fetaqa.keys())[args.start:args.end]

    fw = open(f'outputs/response_s{args.start}_e{args.end}_{dt_string}.json', 'w')
    tmp = {'demonstration': demonstration_prompt}
    fw.write(json.dumps(tmp) + '\n')

    for key in tqdm.tqdm(keys):
        entry = fetaqa[key]

        question = entry['question']
        answer = entry['answer']

        #### Formalizing the k-shot demonstration. #####
        val = 0
        table = entry['table'].strip().strip('\n').strip('\n').split('\n')
        first_row_add = table[0].strip()
        first_col = []
        for l in range(len(table)):
            line = table[l].strip().split(" | ")
            first_col.append(line[0])
        first_col_add = " | ".join(first_col)
        prompt_v2 = prompt_row_or_column + "1. " + first_row_add + "\n2. " + first_col_add + "\nAnswer: "
        # print(prompt_v2)

        response_row_or_column = openai.ChatCompletion.create(
            model=args.model,
            #   prompt=prompt,
            temperature=0.7,
            max_tokens=100,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            messages=[{"role": "user", "content": prompt_v2}]
        )
        response_r_or_c = response_row_or_column['choices'][0]["message"]['content'].strip().strip("\n")
       
        #### Checking of choosing rows or columns
        # print(response_r_or_c)
        # if ("1" in response_r_or_c):
        #     print("1 zaschitalo")
        # else: 
        #     print("2 zaschitalo")
        # print("##########################")
        # continue

        print(prompt_v2)
        print(response_r_or_c)
        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

        if ("1" in response_r_or_c): # The first row contains titles
            prompt_col = demonstration_columns + '\n'
            prompt_col += f'Read the table below regarding "{entry["title"]}" to choose relevant columns for the following questions.\n\n'
            if 'davinci' in args.model:
                prompt_col += '\n'.join(entry['table'].split('\n')[:15])
            else:
                prompt_col += entry['table'].split('\n')[0] + '\n' + entry['table'].split('\n')[1] + '\n' + '\n'
            prompt_col += 'Question: ' + question + '\nRelevant Columns:'

            if args.dry_run:
                print(prompt_col)
                print('answer: ', answer)
            else:
                response = openai.ChatCompletion.create(
                model=args.model,
                #   prompt=prompt,
                temperature=0.7,
                max_tokens=100,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                messages=[{"role": "user", "content": prompt_col}]
                )
                # print(response)
                # continue
                print(prompt_col)
                print(response['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n')[0])
                print("##########################")

                table_processed = decompose_table(entry['table'], response['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n')[0])
                if (len(table_processed.strip('\n')) == 0):
                    table_processed = entry['table']
                # print(table_processed)
                prompt = demonstration_prompt + '\n'
                prompt += f'Read the table below regarding "{entry["title"]}" to answer the following question.\n\n'
                if 'davinci' in args.model:
                    prompt += '\n'.join(entry['table'].split('\n')[:15]) #zabeite
                else:
                    prompt += table_processed + '\n'
                prompt += 'Question: ' + question + '\n'
                prompt += 'Answer:'
                print(prompt)
                response222 = openai.ChatCompletion.create(
                model=args.model,
                #   prompt=prompt,
                temperature=0.7,
                max_tokens=100,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                messages=[{"role": "user", "content": prompt}]
                )
                
                print(response222['choices'][0]["message"]['content'])
                response222 = '\t'.join(response222['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n'))

                tmp = {'key': key, 'question': question, 'response': response222, 'answer': answer, 'table_id': entry['table_id']}

                fw.write(json.dumps(tmp) + '\n')
        else: # The first column contains titles
            prompt_col = demonstration_rows + '\n'
            prompt_col += f'Read the table below regarding "{entry["title"]}" to choose relevant rows for the following questions.\n\n'
            if 'davinci' in args.model:
                prompt_col += '\n'.join(entry['table'].split('\n')[:15])
            else:
                prompt_col += get_two_columns(entry['table']) + '\n' + '\n'
                entry['table'].split('\n')[0] + '\n' + entry['table'].split('\n')[1] + '\n' + '\n'
            prompt_col += 'Question: ' + question + '\nRelevant Titles:'

            if args.dry_run:
                print(prompt_col)
                print('answer: ', answer)
            else:
                response = openai.ChatCompletion.create(
                model=args.model,
                #   prompt=prompt,
                temperature=0.7,
                max_tokens=100,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                messages=[{"role": "user", "content": prompt_col}]
                )
                # print(response)
                # continue
                print(prompt_col)
                print(response['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n')[0])
                print("##########################")

                table_processed = decompose_table_byrows(entry['table'], response['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n')[0])
                if (len(table_processed.strip('\n')) == 0):
                    table_processed = entry['table']
                # print(table_processed)
                prompt = demonstration_prompt_row + '\n'
                prompt += f'Read the table below regarding "{entry["title"]}" to answer the following question.\n\n'
                if 'davinci' in args.model:
                    prompt += '\n'.join(entry['table'].split('\n')[:15]) #zabeite
                else:
                    prompt += table_processed + '\n'
                prompt += 'Question: ' + question + '\n'
                prompt += 'Answer:'
                print(prompt)
                response222 = openai.ChatCompletion.create(
                model=args.model,
                #   prompt=prompt,
                temperature=0.7,
                max_tokens=100,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
                messages=[{"role": "user", "content": prompt}]
                )
                
                print(response222['choices'][0]["message"]['content'])
                response222 = '\t'.join(response222['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n'))

                tmp = {'key': key, 'question': question, 'response': response222, 'answer': answer, 'table_id': entry['table_id']}

                fw.write(json.dumps(tmp) + '\n')


    fw.close()

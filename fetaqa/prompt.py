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
parser.add_argument("--end", required=True, type=int)
parser.add_argument("--dry_run", default=False, action="store_true",
    help="whether it's a dry run or real run.")
parser.add_argument(
    "--temperature", type=float, default=0.7,
    help="temperature of 0 implies greedy sampling.")


demonstration = """
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

demonstration_columns = """
Read the following table regarding "Shagun Sharma" to choose relevant columns for the following question.

Year | Title | Role | Channel

Question: What TV shows was Shagun Sharma seen in 2019?
Answer: Year | Title | Role
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

if __name__ == "__main__":
    args = parser.parse_args()

    # openai.api_key = os.getenv('OPENAI_KEY')
    openai.api_key = ""

    with open(f'test_qa.json') as f:
        fetaqa = json.load(f)

    now = datetime.now() 
    dt_string = now.strftime("%d_%H_%M")

    keys = list(fetaqa.keys())[args.start:args.end]

    fw = open(f'outputs/response_s{args.start}_e{args.end}_{dt_string}.json', 'w')
    tmp = {'demonstration': demonstration}
    fw.write(json.dumps(tmp) + '\n')

    for key in tqdm.tqdm(keys):
        entry = fetaqa[key]

        question = entry['question']
        answer = entry['answer']

        prompt_col = demonstration_columns + '\n'
        prompt_col += f'Read the following table regarding "{entry["title"]}" to choose relevant columns for the following question.\n\n'
        prompt_col += entry['table'].split('\n')[0] + '\n\n'
        prompt_col += 'Question: ' + question + '\nAnswer:'

        if args.dry_run:
            print(prompt_col)
        else:
            response = openai.ChatCompletion.create(
              model="gpt-3.5-turbo",
            #   prompt=prompt,
              temperature=0.7,
              max_tokens=100,
              top_p=1,
              frequency_penalty=0,
              presence_penalty=0,
              messages=[{"role": "user", "content": prompt_col}]
            )

            # response = response['choices'][0]["message"]['content'].strip().strip('\n')

            # prompt = demonstration + '\n'
            # prompt += f'Read the following table regarding "{entry["title"]}" to answer the given question.\n\n'
            # prompt += entry['table'] + '\n\n'
            # prompt += 'Question: ' + question + '\nAnswer:'
            
            table_processed = decompose_table(entry['table'], response['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n')[0])
            print(table_processed)
            prompt = demonstration + '\n'
            prompt += f'Read the following table regarding "{entry["title"]}" to answer the given question.\n\n'
            prompt += table_processed + '\n'
            prompt += 'Question: ' + question + '\nAnswer:'

            print(prompt)
            response222 = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
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


            # tmp = {'key': key, 'question': question, 'response': response, 'answer': answer, 'table_id': entry['table_id']}

            # fw.write(json.dumps(tmp) + '\n')

    fw.close()

import os
import openai
import json
import random
import argparse
import tqdm
import sys
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--option", default='cot', type=str)
parser.add_argument("--model", default='gpt-3.5-turbo', type=str)
parser.add_argument("--start", required=True, type=int)
parser.add_argument("--end", required=True, type=int)
parser.add_argument("--dry_run", default=False, action="store_true",
    help="whether it's a dry run or real run.")
parser.add_argument(
    "--temperature", type=float, default=0.7,
    help="temperature of 0 implies greedy sampling.")

demonstration = {}
demonstration['direct'] = """
Read the table below regarding "2008 Clásica de San Sebastián" to answer the following questions.

Rank | Cyclist | Team | Time | UCI ProTour Points
1 | Alejandro Valverde (ESP) | Caisse d'Epargne | 5h 29' 10 | 40
2 | Alexandr Kolobnev (RUS) | Team CSC Saxo Bank | s.t. | 30
3 | Davide Rebellin (ITA) | Gerolsteiner | s.t. | 25
4 | Paolo Bettini (ITA) | Quick Step | s.t. | 20
5 | Franco Pellizotti (ITA) | Liquigas | s.t. | 15
6 | Denis Menchov (RUS) | Rabobank | s.t. | 11
7 | Samuel Sánchez (ESP) | Euskaltel-Euskadi | s.t. | 7
8 | Stéphane Goubert (FRA) | Ag2r-La Mondiale | + 2 | 5
9 | Haimar Zubeldia (ESP) | Euskaltel-Euskadi | + 2 | 3
10 | David Moncoutié (FRA) | Cofidis | + 2 | 1

read the question first, and then answer the given question. 

Question: which country had the most cyclists finish within the top 10?
The answer is Italy.

Question: how many players got less than 10 points?
The answer is 4.

Question: how many points does the player from rank 3, rank 4 and rank 5 combine to have? 
The answer is 60.

Question: who spent the most time in the 2008 Clásica de San Sebastián. 
The answer is David Moncoutié.
"""

demonstration['cot'] = """
Read the table below regarding "2008 Clásica de San Sebastián" to answer the following questions.

Rank | Cyclist | Team | Time | UCI ProTour Points
1 | Alejandro Valverde (ESP) | Caisse d'Epargne | 5h 29' 10 | 40
2 | Alexandr Kolobnev (RUS) | Team CSC Saxo Bank | s.t. | 30
3 | Davide Rebellin (ITA) | Gerolsteiner | s.t. | 25
4 | Paolo Bettini (ITA) | Quick Step | s.t. | 20
5 | Franco Pellizotti (ITA) | Liquigas | s.t. | 15
6 | Denis Menchov (RUS) | Rabobank | s.t. | 11
7 | Samuel Sánchez (ESP) | Euskaltel-Euskadi | s.t. | 7
8 | Stéphane Goubert (FRA) | Ag2r-La Mondiale | + 2 | 5
9 | Haimar Zubeldia (ESP) | Euskaltel-Euskadi | + 2 | 3
10 | David Moncoutié (FRA) | Cofidis | + 2 | 1

Question: which country had the most cyclists finish within the top 10?
Explanation: ITA occurs three times in the table, more than any others. Therefore, the answer is Italy.

Question: how many players got less than 10 points?
Explanation: Samuel Sánchez,  Stéphane Goubert, Haimar Zubeldia and David Moncoutié received less than 10 points.  Therefore, the answer is 4.

Question: how many points does the player from rank 3, rank 4 and rank 5 combine to have? 
Explanation: rank 3 has 25 points, rank 4 has 20 points, rank 5 has 15 points, they combine to have a total of 60 points. Therefore, the answer is 60.

Question: who spent the most time in the 2008 Clásica de San Sebastián?
Explanation: David Moncoutié spent the most time to finish the game and ranked the last. Therefore, the answer is David Moncoutié.
"""

demonstration['question_decomp'] = """
Read the table below regarding "2008 Clásica de San Sebastián" to answer the following questions.

Rank | Cyclist | Team | Time | UCI ProTour Points
1 | Alejandro Valverde (ESP) | Caisse d'Epargne | 5h 29' 10 | 40
2 | Alexandr Kolobnev (RUS) | Team CSC Saxo Bank | s.t. | 30
3 | Davide Rebellin (ITA) | Gerolsteiner | s.t. | 25
4 | Paolo Bettini (ITA) | Quick Step | s.t. | 20
5 | Franco Pellizotti (ITA) | Liquigas | s.t. | 15
6 | Denis Menchov (RUS) | Rabobank | s.t. | 11
7 | Samuel Sánchez (ESP) | Euskaltel-Euskadi | s.t. | 7
8 | Stéphane Goubert (FRA) | Ag2r-La Mondiale | + 2 | 5
9 | Haimar Zubeldia (ESP) | Euskaltel-Euskadi | + 2 | 3
10 | David Moncoutié (FRA) | Cofidis | + 2 | 1

Question: which country had the most cyclists finish within the top 10?
Decomposed Table: The question requires only Rank and Cyclist columns.
Rank | Cyclist
1 | Alejandro Valverde (ESP)
2 | Alexandr Kolobnev (RUS)
3 | Davide Rebellin (ITA)
4 | Paolo Bettini (ITA)
5 | Franco Pellizotti (ITA)
6 | Denis Menchov (RUS)
7 | Samuel Sánchez (ESP)
8 | Stéphane Goubert (FRA)
9 | Haimar Zubeldia (ESP)
10 | David Moncoutié (FRA)
Explanation: ITA occurs three times in the table, more than any others. Therefore, the answer is Italy.

Question: how many players got less than 10 points?
Decomposed Table: The question requires only Cyclist and UCI ProTour Points columns.
Cyclist | UCI ProTour Points
Alejandro Valverde (ESP) | 40
Alexandr Kolobnev (RUS) | 30
Davide Rebellin (ITA) | 25
Paolo Bettini (ITA) | 20
Franco Pellizotti (ITA) | 15
Denis Menchov (RUS) | 11
Samuel Sánchez (ESP) | 7
Stéphane Goubert (FRA) | 5
Haimar Zubeldia (ESP) | 3
David Moncoutié (FRA) | 1
Explanation: Samuel Sánchez,  Stéphane Goubert, Haimar Zubeldia and David Moncoutié received less than 10 points.  Therefore, the answer is 4.

Question: how many points does the player from rank 3, rank 4 and rank 5 combine to have?
Decomposed Table: The question requires only Rank and UCI ProTour Points columns.
Rank | UCI ProTour Points
1 | 40
2 | 30
3 | 25
4 | 20
5 | 15
6 | 11
7 | 7
8 | 5
9 | 3
10 | 1
Explanation: rank 3 has 25 points, rank 4 has 20 points, rank 5 has 15 points, they combine to have a total of 60 points. Therefore, the answer is 60.

Question: who spent the most time in the 2008 Clásica de San Sebastián?
Decomposed Table: The question requires only Rank, Cyclist and Time columns.
Rank | Cyclist | Time
1 | Alejandro Valverde (ESP) | 5h 29' 10
2 | Alexandr Kolobnev (RUS) | s.t.
3 | Davide Rebellin (ITA) | s.t.
4 | Paolo Bettini (ITA) | s.t.
5 | Franco Pellizotti (ITA) | s.t.
6 | Denis Menchov (RUS) | s.t.
7 | Samuel Sánchez (ESP) | s.t.
8 | Stéphane Goubert (FRA) | + 2
9 | Haimar Zubeldia (ESP) | + 2
10 | David Moncoutié (FRA) | + 2
Explanation: David Moncoutié spent the most time to finish the game and ranked the last. Therefore, the answer is David Moncoutié.
"""

demonstration_columns = {}

demonstration_columns['cot'] = """
Read the columns below regarding "2008 Clásica de San Sebastián" table to choose relevant columns for the following questions.

Rank | Cyclist | Team | Time | UCI ProTour Points

Question: which country had the most cyclists finish within the top 10?
Answer: Rank | Cyclist

Question: how many players got less than 10 points?
Answer: Cyclist | UCI ProTour Points.

Question: how many points does the player from rank 3, rank 4 and rank 5 combine to have?
Answer: Rank | UCI ProTour Points

Question: who spent the most time in the 2008 Clásica de San Sebastián?
Answer: Rank | Cyclist | Time
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

    # openai.api_key = os.getenv('OPENAI_API_KEY')
    openai.api_key = "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"
    with open(f'test_qa.json') as f:
        wikitableqa = json.load(f)

    now = datetime.now() 
    dt_string = now.strftime("%d_%H_%M")

    keys = list(wikitableqa.keys())[args.start:args.end]

    correct = 0
    wrong = 0

    if not args.dry_run:
        model_version = args.model.split('-')[1]
        fw = open(f'outputs/response_s{args.start}_e{args.end}_{args.option}_{model_version}_{dt_string}.json', 'w')
        tmp = {'demonstration': demonstration[args.option]}
        fw.write(json.dumps(tmp) + '\n')

    for key in tqdm.tqdm(keys):
        entry = wikitableqa[key]

        question = entry['question']
        answer = entry['answer']

        #### Formalizing the k-shot demonstration. #####
        prompt_col = demonstration_columns[args.option] + '\n'
        prompt_col += f'Read the columns below regarding "{entry["title"]}" to choose relevant columns for the following questions.\n\n'
        if 'davinci' in args.model:
            prompt_col += '\n'.join(entry['table'].split('\n')[:15])
        else:
            prompt_col += entry['table'].split('\n')[0] + '\n' + '\n'
        prompt_col += 'Question: ' + question + '\nAnswer:'

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

            table_processed = decompose_table(entry['table'], response['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n')[0])
            # print(table_processed)
            prompt = demonstration[args.option] + '\n'
            prompt += f'Read the table below regarding "{entry["title"]}" to answer the following question.\n\n'
            if 'davinci' in args.model:
                prompt += '\n'.join(entry['table'].split('\n')[:15]) #zabeite
            else:
                prompt += table_processed + '\n'
            prompt += 'Question: ' + question + '\nExplanation:'

            # print(prompt)
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
            
            # print(response222['choices'][0]["message"]['content'])
            response222 = '\t'.join(response222['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n'))

            tmp = {'key': key, 'question': question, 'response': response222, 'answer': answer, 'table_id': entry['table_id']}

            fw.write(json.dumps(tmp) + '\n')

    if not args.dry_run:
        print(correct, wrong, correct / (correct + wrong + 0.001))
        fw.close()

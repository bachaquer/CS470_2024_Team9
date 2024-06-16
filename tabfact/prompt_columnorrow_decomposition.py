import os
import openai
import json
import random
import argparse
import tqdm
import sys
from datetime import datetime

parser = argparse.ArgumentParser()
parser.add_argument("--channel", required=True, type=str)
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
demonstration["direct"] = {}
demonstration["direct"]["simple"] = """
Read the table below regarding "2002 u.s. open (golf)" to verify whether the provided claims are true or false.

place | player | country | score | to par
1 | tiger woods | united states | 67 + 68 + 70 = 205 | - 5
2 | sergio garcía | spain | 68 + 74 + 67 = 209 | - 1
t3 | jeff maggert | united states | 69 + 73 + 68 = 210 | e
t3 | phil mickelson | united states | 70 + 73 + 67 = 210 | e
t5 | robert allenby | australia | 74 + 70 + 67 = 211 | + 1
t5 | pádraig harrington | ireland | 70 + 68 + 73 = 211 | + 1
t5 | billy mayfair | united states | 69 + 74 + 68 = 211 | + 1
t8 | nick faldo | england | 70 + 76 + 66 = 212 | + 2
t8 | justin leonard | united states | 73 + 71 + 68 = 212 | + 2
t10 | tom byrum | united states | 72 + 72 + 70 = 214 | + 4
t10 | davis love iii | united states | 71 + 71 + 72 = 214 | + 4
t10 | scott mccarron | united states | 72 + 72 + 70 = 214 | + 4

Claim: nick faldo is the only player from england.
Explanation: the claim is true.

Claim: justin leonard score less than 212 which put him tied for the 8th place.
Explanation: the claim is false.

Claim: when player is phil mickelson, the total score is 210.
Explanation: the claim is true.
"""
demonstration["direct"]["complex"] = """
Read the table below regarding "1919 in brazilian football" to verify whether the provided claims are true or false.

date | result | score | brazil scorers | competition
may 11 , 1919 | w | 6 - 0 | friedenreich (3) , neco (2) , haroldo | south american championship
may 18 , 1919 | w | 6 - 1 | heitor , amílcar (4), millon | south american championship
may 26 , 1919 | w | 5 - 2  | neco (5) | south american championship
may 30 , 1919 | l | 1 - 2 | jesus (1) | south american championship
june 2nd , 1919 | l | 0 - 2 | - | south american championship

Claim: neco has scored a total of 7 goals in south american championship.
Explanation: the claim is true.

Claim: jesus has scored in two games in south american championship.
Explanation: the claim is false.

Claim: brazilian football has participated in five games in may, 1919.
Explanation: the claim is false.

Claim: brazilian football played games between may and july.
Explanation: the claim is true. 
"""
demonstration["cot"] = {}
demonstration["cot"]["simple"] = """
Read the table below regarding "2002 u.s. open (golf)" to verify whether the provided claims are true or false.

place | player | country | score | to par
1 | tiger woods | united states | 67 + 68 + 70 = 205 | - 5
2 | sergio garcía | spain | 68 + 74 + 67 = 209 | - 1
t3 | jeff maggert | united states | 69 + 73 + 68 = 210 | e
t3 | phil mickelson | united states | 70 + 73 + 67 = 210 | e
t5 | robert allenby | australia | 74 + 70 + 67 = 211 | + 1
t5 | pádraig harrington | ireland | 70 + 68 + 73 = 211 | + 1
t5 | billy mayfair | united states | 69 + 74 + 68 = 211 | + 1
t8 | nick faldo | england | 70 + 76 + 66 = 212 | + 2
t8 | justin leonard | united states | 73 + 71 + 68 = 212 | + 2
t10 | tom byrum | united states | 72 + 72 + 70 = 214 | + 4
t10 | davis love iii | united states | 71 + 71 + 72 = 214 | + 4
t10 | scott mccarron | united states | 72 + 72 + 70 = 214 | + 4

Claim: nick faldo is the only player from england.
Explanation: no other player is from england, therefore, the claim is true.

Claim: justin leonard score less than 212 which put him tied for the 8th place.
Explanation: justin leonard scored exactly 212, therefore, the claim is false.
"""
demonstration["cot"]["complex"] = """
Read the table below regarding "1919 in brazilian football" to verify whether the provided claims are true or false.

date | result | score | brazil scorers | competition
may 11 , 1919 | w | 6 - 0 | friedenreich (3) , neco (2) , haroldo | south american championship
may 18 , 1919 | w | 6 - 1 | heitor , amílcar (4), millon | south american championship
may 26 , 1919 | w | 5 - 2  | neco (5) | south american championship
may 30 , 1919 | l | 1 - 2 | jesus (1) | south american championship
june 2nd , 1919 | l | 0 - 2 | - | south american championship

Claim: neco has scored a total of 7 goals in south american championship.
Explanation: neco has scored 2 goals on may 11  and 5 goals on may 26. neco has scored a total of 7 goals, therefore, the claim is true.

Claim: jesus has scored in two games in south american championship.
Explanation: jesus only scored once on the may 30 game, but not in any other game, therefore, the claim is false.

Claim: brazilian football team has scored six goals twice in south american championship.
Explanation: brazilian football team scored six goals once on may 11 and once on may 18, twice in total, therefore, the claim is true.
"""

"""
Claim: brazilian football has participated in five games in may, 1919.
Explanation:  brazilian football only participated in four games rather than five games, therefore, the claim is false.

Claim: brazilian football played games between may and july.
Explanation: brazilian football played on june 2nd, which is between may and july, therefore, the claim is true

Claim: brazilian football team scored at least 1 goals in all the 1919 matches.
Explanation: the team scored zero goal on june 2nd, which is less than 1 goals, therefore, the claim is false.

Claim: brazilian football team has won 2 games and lost 3 games.
Explanation: the team only lost 2 games instead of 3 games, therefore, the claim is false.
"""

demonstration_columns = {}
demonstration_columns['simple'] = """
Read the table below regarding "2002 u.s. open (golf)" to choose relevant columns to verify the following claims.

place | player | country | score | to par
1 | tiger woods | united states | 67 + 68 + 70 = 205 | - 5

Claim: nick faldo is the only player from england.
Relevant Columns: player | country

Claim: justin leonard score less than 212 which put him tied for the 8th place.
Relevant Columns: place | player | score

Claim: when player is phil mickelson, the total score is 210.
Relevant Columns: player | score
"""
demonstration_columns['complex'] = """
Read the table below regarding "1919 in brazilian football" to choose relevant columns to verify the following claims.

date | result | score | brazil scorers | competition
may 11 , 1919 | w | 6 - 0 | friedenreich (3) , neco (2) , haroldo | south american championship

Claim: neco has scored a total of 7 goals in south american championship.
Relevant Columns: score | brazil scorers | competition

Claim: jesus has scored in two games in south american championship.
Relevant Columns: score | brazil scorers | competition

Claim: brazilian football has participated in five games in may, 1919.
Relevant Columns: date | brazil scorers | competition

Claim: brazilian football played games between may and july.
Relevant Columns: date | brazil scorers | competition
"""


############

demonstration_row_type = {}
demonstration_row_type["direct"] = {}
demonstration_row_type["direct"]["simple"] = """
Read the table below regarding "2002 u.s. open (golf)" to verify whether the provided claims are true or false.

place | 1 | 2 | t3 | t3 | t5 | t5 | t5 | t8 | t8 | t10 | t10 | t10
player | tiger woods | sergio garcía | jeff maggert | phil mickelson | robert allenby | pádraig harrington | billy mayfair | nick faldo | justin leonard | tom byrum | davis love iii | scott mccarron
country | united states | spain | united states | united states | australia | ireland | united states | england | united states | united states | united states | united states
score | 67 + 68 + 70 = 205 | 68 + 74 + 67 = 209 | 69 + 73 + 68 = 210 | 70 + 73 + 67 = 210 | 74 + 70 + 67 = 211 | 70 + 68 + 73 = 211 | 69 + 74 + 68 = 211 | 70 + 76 + 66 = 212 | 73 + 71 + 68 = 212 | 72 + 72 + 70 = 214 | 71 + 71 + 72 = 214 | 72 + 72 + 70 = 214
to par | - 5 | - 1 | e | e | + 1 | + 1 | + 1 | + 2 | + 2 | + 4 | + 4 | + 4

Claim: nick faldo is the only player from england.
Explanation: the claim is true.

Claim: justin leonard score less than 212 which put him tied for the 8th place.
Explanation: the claim is false.

Claim: when player is phil mickelson, the total score is 210.
Explanation: the claim is true.
"""
demonstration_row_type["direct"]["complex"] = """
Read the table below regarding "1919 in brazilian football" to verify whether the provided claims are true or false.

date | may 11 , 1919 | may 18 , 1919 | may 26 , 1919 | may 30 , 1919 | june 2nd , 1919
result | w | w | w | l | l
score | 6 - 0 | 6 - 1 | 5 - 2 | 1 - 2 | 0 - 2
brazil scorers | friedenreich (3) , neco (2) , haroldo | heitor , amílcar (4), millon | neco (5) | jesus (1) | -
competition | south american championship | south american championship | south american championship | south american championship | south american championship

Claim: neco has scored a total of 7 goals in south american championship.
Explanation: the claim is true.

Claim: jesus has scored in two games in south american championship.
Explanation: the claim is false.

Claim: brazilian football has participated in five games in may, 1919.
Explanation: the claim is false.

Claim: brazilian football played games between may and july.
Explanation: the claim is true. 
"""
demonstration_row_type["cot"] = {}
demonstration_row_type["cot"]["simple"] = """
Read the table below regarding "2002 u.s. open (golf)" to verify whether the provided claims are true or false.

place | 1 | 2 | t3 | t3 | t5 | t5 | t5 | t8 | t8 | t10 | t10 | t10
player | tiger woods | sergio garcía | jeff maggert | phil mickelson | robert allenby | pádraig harrington | billy mayfair | nick faldo | justin leonard | tom byrum | davis love iii | scott mccarron
country | united states | spain | united states | united states | australia | ireland | united states | england | united states | united states | united states | united states
score | 67 + 68 + 70 = 205 | 68 + 74 + 67 = 209 | 69 + 73 + 68 = 210 | 70 + 73 + 67 = 210 | 74 + 70 + 67 = 211 | 70 + 68 + 73 = 211 | 69 + 74 + 68 = 211 | 70 + 76 + 66 = 212 | 73 + 71 + 68 = 212 | 72 + 72 + 70 = 214 | 71 + 71 + 72 = 214 | 72 + 72 + 70 = 214
to par | - 5 | - 1 | e | e | + 1 | + 1 | + 1 | + 2 | + 2 | + 4 | + 4 | + 4

Claim: nick faldo is the only player from england.
Explanation: no other player is from england, therefore, the claim is true.

Claim: justin leonard score less than 212 which put him tied for the 8th place.
Explanation: justin leonard scored exactly 212, therefore, the claim is false.
"""
demonstration_row_type["cot"]["complex"] = """
Read the table below regarding "1919 in brazilian football" to verify whether the provided claims are true or false.

date | may 11 , 1919 | may 18 , 1919 | may 26 , 1919 | may 30 , 1919 | june 2nd , 1919
result | w | w | w | l | l
score | 6 - 0 | 6 - 1 | 5 - 2 | 1 - 2 | 0 - 2
brazil scorers | friedenreich (3) , neco (2) , haroldo | heitor , amílcar (4), millon | neco (5) | jesus (1) | -
competition | south american championship | south american championship | south american championship | south american championship | south american championship

Claim: neco has scored a total of 7 goals in south american championship.
Explanation: neco has scored 2 goals on may 11  and 5 goals on may 26. neco has scored a total of 7 goals, therefore, the claim is true.

Claim: jesus has scored in two games in south american championship.
Explanation: jesus only scored once on the may 30 game, but not in any other game, therefore, the claim is false.

Claim: brazilian football team has scored six goals twice in south american championship.
Explanation: brazilian football team scored six goals once on may 11 and once on may 18, twice in total, therefore, the claim is true.
"""

demonstration_rows = {}
demonstration_rows['simple'] = """
Read the table below regarding "2002 u.s. open (golf)" to choose relevant rows to verify the following claims.

place | 1
player | tiger woods
country | united states
score | 67 + 68 + 70 = 205
to par | - 5

Claim: nick faldo is the only player from england.
Relevant Titles: player | country

Claim: justin leonard score less than 212 which put him tied for the 8th place.
Relevant Titles: place | player | score

Claim: when player is phil mickelson, the total score is 210.
Relevant Titles: player | score
"""
demonstration_rows['complex'] = """
Read the table below regarding "1919 in brazilian football" to choose relevant rows to verify the following claims.

date | may 11 , 1919
result | w
score | 6 - 0
brazil scorers | friedenreich (3) , neco (2) , haroldo
competition | south american championship

Claim: neco has scored a total of 7 goals in south american championship.
Relevant Titles: score | brazil scorers | competition

Claim: jesus has scored in two games in south american championship.
Relevant Titles: score | brazil scorers | competition

Claim: brazilian football has participated in five games in may, 1919.
Relevant Titles: date | brazil scorers | competition

Claim: brazilian football played games between may and july.
Relevant Titles: date | brazil scorers | competition
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
    with open(f'test_statements_{args.channel}.json') as f:
        tabfact = json.load(f)

    now = datetime.now() 
    dt_string = now.strftime("%d_%H_%M")

    keys = list(tabfact.keys())[args.start:args.end]

    correct = 0
    wrong = 0

    if not args.dry_run:
        model_version = args.model.split('-')[1]
        fw = open(f'outputs/response_s{args.start}_e{args.end}_{args.channel}_{args.option}_{model_version}_{dt_string}.json', 'w')
        tmp = {'demonstration': demonstration[args.option][args.channel]}
        fw.write(json.dumps(tmp) + '\n')


    for key in tqdm.tqdm(keys):
        entry = tabfact[key]

        statement = entry['statement']
        label = entry['label']

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
            prompt_col = demonstration_columns[args.channel] + '\n'
            prompt_col += f'Read the table below regarding "{entry["title"]}" to choose relevant columns for the following questions.\n\n'
            if 'davinci' in args.model:
                prompt_col += '\n'.join(entry['table'].split('\n')[:15])
            else:
                prompt_col += entry['table'].split('\n')[0] + '\n' + entry['table'].split('\n')[1] + '\n' + '\n'
            prompt_col += 'Claim: ' + statement + '\nRelevant Columns:'

            if args.dry_run:
                print(prompt_col)
                # print('answer: ', answer)
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
                prompt = demonstration[args.option][args.channel] + '\n'
                prompt += f'Read the table below regarding "{entry["title"]}" to verify whether the provided claim is true or false.\n\n'
                if 'davinci' in args.model:
                    prompt += '\n'.join(entry['table'].split('\n')[:15]) #zabeite
                else:
                    prompt += table_processed + '\n'
                prompt += 'Claim: ' + statement + '\n'
                if (args.option == 'cot'):
                    prompt += 'Explanation:'
                else:
                    prompt += 'Explanation:'
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
                if 'true' in response222:
                    predict = 1
                elif 'false' in response222:
                    predict = 0
                elif 'support' in response222:
                    predict = 1
                else:
                    predict = 0

                if predict == label:
                    correct += 1
                else:
                    wrong += 1

                tmp = {'key': key, 'statement': statement, 'response': response, 'label': label, 'prediction': predict}

                fw.write(json.dumps(tmp) + '\n')
        else: # The first column contains titles
            prompt_col = demonstration_rows[args.channel] + '\n'
            prompt_col += f'Read the table below regarding "{entry["title"]}" to choose relevant rows for the following questions.\n\n'
            if 'davinci' in args.model:
                prompt_col += '\n'.join(entry['table'].split('\n')[:15])
            else:
                prompt_col += get_two_columns(entry['table']) + '\n' + '\n'
                entry['table'].split('\n')[0] + '\n' + entry['table'].split('\n')[1] + '\n' + '\n'
            prompt_col += 'Claim: ' + statement + '\nRelevant Titles:'

            if args.dry_run:
                print(prompt_col)
                # print('answer: ', answer)
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
                prompt = demonstration_row_type[args.option][args.channel] + '\n'
                prompt += f'Read the table below regarding "{entry["title"]}" to verify whether the provided claim is true or false.\n\n'
                if 'davinci' in args.model:
                    prompt += '\n'.join(entry['table'].split('\n')[:15]) #zabeite
                else:
                    prompt += table_processed + '\n'
                prompt += 'Claim: ' + statement + '\n'
                if (args.option == 'cot'):
                    prompt += 'Explanation:'
                else:
                    prompt += 'Explanation:'
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
                if 'true' in response222:
                    predict = 1
                elif 'false' in response222:
                    predict = 0
                elif 'support' in response222:
                    predict = 1
                else:
                    predict = 0

                if predict == label:
                    correct += 1
                else:
                    wrong += 1

                tmp = {'key': key, 'statement': statement, 'response': response, 'label': label, 'prediction': predict}

                fw.write(json.dumps(tmp) + '\n')


    if not args.dry_run:
        print(correct, wrong, correct / (correct + wrong + 0.001))
        fw.close()

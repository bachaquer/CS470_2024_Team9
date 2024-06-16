import os
import openai
import json
import random
import argparse
import tqdm
import sys
from datetime import datetime
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
Explanation: player | country

Claim: justin leonard score less than 212 which put him tied for the 8th place.
Explanation: place | player | score

Claim: when player is phil mickelson, the total score is 210.
Explanation: player | score
"""
demonstration_columns['complex'] = """
Read the table below regarding "1919 in brazilian football" to choose relevant columns to verify the following claims.

date | result | score | brazil scorers | competition
may 11 , 1919 | w | 6 - 0 | friedenreich (3) , neco (2) , haroldo | south american championship
may 18 , 1919 | w | 6 - 1 | heitor , amílcar (4), millon | south american championship
may 26 , 1919 | w | 5 - 2  | neco (5) | south american championship
may 30 , 1919 | l | 1 - 2 | jesus (1) | south american championship
june 2nd , 1919 | l | 0 - 2 | - | south american championship

Claim: neco has scored a total of 7 goals in south american championship.
Explanation: score | brazil scorers | competition

Claim: jesus has scored in two games in south american championship.
Explanation: score | brazil scorers | competition

Claim: brazilian football has participated in five games in may, 1919.
Explanation: date | brazil scorers | competition

Claim: brazilian football played games between may and july.
Explanation: date | brazil scorers | competition
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

        # #### Formalizing the k-shot demonstration. #####
        # prompt = demonstration[args.option][args.channel] + '\n'
        # prompt += f'Read the table below regarding "{entry["title"]}" to verify whether the provided claim is true or false.\n\n'
        # # prompt += f'Title: {entry["title"]}:\n'
        # prompt += entry['table'] + '\n'
        # # prompt += 'Please verify whether following claim is true or false.\n\n'
        # prompt += 'Claim: ' + statement + '\n' + 'Explanation:'

        prompt_col = demonstration_columns[args.channel] + '\n'
        prompt_col += f'Read the table below regarding "{entry["title"]}" to choose relevant columns to verify the following claims.\n\n'
        prompt_col += entry['table'].split('\n')[0] + '\n\n'
        prompt_col += 'Claim: ' + statement + '\nExplanation:'

        if args.dry_run:
            print('------------------------------------------------', key)
            print(prompt_col)
            print()
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

            table_processed = decompose_table(entry['table'], response['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n')[0])
            print(table_processed)
            prompt = demonstration[args.option][args.channel] + '\n'
            prompt += f'Read the table below regarding "{entry["title"]}" to verify whether the provided claim is true or false.\n\n'
            prompt += table_processed + '\n'
            prompt += 'Claim: ' + statement + '\n' + 'Explanation:'

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
            response222 = response222['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n')[0]
            # response = response['choices'][0]["message"]['content'].strip().strip('\n').strip('\n').split('\n')[0]
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
        print(correct, wrong, correct / (correct + wrong))
        fw.close()
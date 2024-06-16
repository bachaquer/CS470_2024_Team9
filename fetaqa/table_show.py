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


if __name__ == "__main__":
    args = parser.parse_args()

    with open(f'test_qa.json') as f:
        fetaqa = json.load(f)

    now = datetime.now() 
    dt_string = now.strftime("%d_%H_%M")

    keys = list(fetaqa.keys())[args.start:args.end]

    for key in tqdm.tqdm(keys):
        entry = fetaqa[key]
        print("")

        question = entry['question']
        answer = entry['answer']
        print(entry['table'])
        a = input("continue? y/n")
        print("##################################")
        if (a == 'n'):
            break
        continue

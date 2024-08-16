#!/usr/bin/env python3
import argparse
import os
import shutil
from pathlib import Path
import datetime
import logging

def fix_second(path):
    if not path[0:2] == './':
        path = './' + path
    files = path.split('/')
    files.pop(1)
    return '/'.join(files)[1:]


def process_file(file_name):
    file_set = set()
    with open(file_name) as f:
        for line in f:
            split_1 = line.split(',')
            split_2 = line.split('  .')
            if len(split_2) == 2:
                pair = (split_2[0].strip(), split_2[1].strip())
                file_set.add(pair)
            else:
                pair = (split_1[1].strip(), fix_second(split_1[3]).strip())
                file_set.add(pair)

    return file_set


def copy_difference(path, set_diff):
    if not set_diff:
        logging.warning('Set has no difference - copy not created')
        return

    dir_path = path.rsplit('.', 2)[0]
    dir_path_update = dir_path + '_update'
    
    for _,item in set_diff:
        directory = os.path.dirname(dir_path_update + item)
        Path(directory).mkdir(parents=True, exist_ok=True)
        shutil.copy(dir_path + item, dir_path_update + item)
    logging.info(f'Copy has been created at path {dir_path_update}')


def main():
    parser = argparse.ArgumentParser(description='Compare two md5deep file listing files') 
    parser.add_argument('file1',metavar='file1',
                        help='md5deep file listing file 1')
    parser.add_argument('file2',metavar='file2',
                        help='md5deep file listing file 2')
    parser.add_argument('-a',action='store_true',
                        help='show all files')
    parser.add_argument('-c',nargs=1,metavar='num',
                        help='copy diff of files in a given direction')
    args = parser.parse_args()

    date = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    console_handler = logging.StreamHandler()
    logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(message)s',
                        level=logging.DEBUG,
                        handlers=[console_handler])

    set1 = process_file(args.file1)
    set2 = process_file(args.file2)

    if len(set1) == len(set2) and set1 == set2:
        logging.info('File 1 and file 2 are the same')
    else:
        if args.a:
            for item in set1 - set2:
                logging.info(f'1 - 2: {item}')
            for item in set2 - set1:
                logging.info(f'2 - 1: {item}')
        logging.info(f'File 1 contains {len(set1)} files and has {len(set1 - set2)} files that file 2 does not (1 - 2)')
        logging.info(f'File 2 contains {len(set2)} files and has {len(set2 - set1)} files that file 1 does not (2 - 1)')
    
    if args.c:
        if args.c[0] == '2':
            copy_difference(args.file2, set2 - set1)
        elif args.c[0] == '1':
            copy_difference(args.file1, set1 - set2)
        else:
            logging.error('Invalid arguments for copying (must be 1 or 2)')


if __name__ == "__main__":
    main()

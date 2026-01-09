#!/usr/bin/env python3
import argparse
import os
import shutil
from pathlib import Path
import datetime
import logging
import re
import sys


def fix_second(path):
    if not path[0:2] == './':
        path = './' + path
    files = path.split('/')
    files.pop(1)
    return '/'.join(files)[1:]


def are_paths_similar(path1, path2, cutoff_percentage=0.4):
    """
    Compares two file paths and returns True if they are considered similar 
    based on a cutoff percentage of how much of either path would need to be 
    chopped off for them to match. Returns False otherwise.
    
    Parameters:
    - path1 (str): The first file path.
    - path2 (str): The second file path.
    - cutoff_percentage (float): The percentage threshold (default is 0.4 or 40%).
    
    Returns:
    - bool: True if the paths are similar based on the given criteria, False otherwise.
    """
    
    # Find the first point where the strings start matching
    min_len = min(len(path1), len(path2))
    
    match_index = -1
    for i in range(min_len):
        if path1[-(i + 1):] == path2[-(i + 1):]:
            match_index = i
        else:
            break
    
    # If no match found at all, return False
    if match_index == -1:
        return False
    
    # Calculate the number of characters to be cut off for each path to match
    cut1 = len(path1) - match_index - 1
    cut2 = len(path2) - match_index - 1
    
    # Calculate the percentage of the path that would be cut off
    perc1 = cut1 / len(path1)
    perc2 = cut2 / len(path2)
    
    # Return True if both percentages are within the cutoff threshold
    return perc1 <= cutoff_percentage and perc2 <= cutoff_percentage


def subtract_sets_with_similar_paths(set1, set2, ignore_hashes, ignore_paths, cutoff_percentage=0.4):
    """
    Compares two sets of (hash, path) pairs and returns the differences between them
    using path similarity instead of direct path comparison.

    Parameters:
    - set1: A set of (hash, path) tuples representing files from the first md5deep file.
    - set2: A set of (hash, path) tuples representing files from the second md5deep file.
    - cutoff_percentage: The percentage of path that can be chopped off to consider them similar.

    Returns:
    - unique_to_set1: Items unique to set1 based on hash and path similarity.
    - unique_to_set2: Items unique to set2 based on hash and path similarity.
    """

    def find_similar_or_exact(item, comparison_set):
        """
        Helper function to find a file in the comparison_set that either has the same hash and similar path,
        or exactly matches both hash and path.
        """
        for other_item in comparison_set:
            hash1, path1 = item
            hash2, path2 = other_item
            if ignore_hashes:
                if are_paths_similar(path1, path2, cutoff_percentage):
                    return True
            elif ignore_paths:
                if hash1 == hash2:
                    return True
            else:
                if hash1 == hash2 and are_paths_similar(path1, path2, cutoff_percentage):
                    return True
        return False

    # Find items in set1 that are not in set2
    unique_to_set1 = {item for item in set1 if not find_similar_or_exact(item, set2)}

    # Find items in set2 that are not in set1
    unique_to_set2 = {item for item in set2 if not find_similar_or_exact(item, set1)}

    return unique_to_set1, unique_to_set2


def process_file(file_name, excluded_pairs, ignore_hashes_set, exclude_path_list=None, include_path_list=None):
    file_set = set()
    with open(file_name) as f:
        for line in f:
            split_1 = line.split(',') # This variable be a list of substrings of the line separated by commas (not including the commas).
            split_2 = line.split() # This variable is useful for manifest files that contain only two columns (hash, filepath) separated by a space or multiple spaces.

            # Determine which format of md5deep file we are dealing with and construct (hash, filepath) pairs for each line accordingly.
            # This is the regular md5deep format that you get by running the md5deep command. 
            if len(split_1) == 4:
                pair = (split_1[1].strip(), split_1[3].strip())
            # Distros in the OpenVDM/OpenRVDAS format will have an md5deep file called "md5_summary.txt"
            # and these are different because they don't only have 2 columns.
            elif len(split_2) == 4: # this is a new format! WHOI is sending space delimited files with 4 columns
                pair = (split_2[1].strip(), split_2[3].strip())
            elif len(split_2) == 2:
                pair = (split_2[0].strip(), split_2[1].strip())
            # edu.washington have started creating md5deep files. They're format contains 3 columns (file size, hash, absolute path). These look similar to the 4-column md5deep files except they're missing the date column. The delimiter for both is a comma.
            elif len(split_1) == 3:
                pair = (split_1[1].strip(), split_1[2].strip())
            else:
                # If we've not found either 2 or 4 commas then I don't recognize this manifest file so just skip this line.
                continue

            if exclude_path_list:
                # Check if any regex pattern in the list matches the path (pair[1])
                if any(re.search(pattern, pair[1]) for pattern in exclude_path_list):
                    excluded_pairs.append(pair)
                    continue

            if include_path_list:
                # Check if the path is included in the include_path_list regex. If not then don't add the pair for consideration.
                if not (any(re.search(pattern, pair[1]) for pattern in include_path_list)):
                    excluded_pairs.append(pair)
                    continue

            # Exclude pairs with hash values equal to the long string of asterisks hashes unless the user has elected not to compare hashes.
            if pair[0] == '********************************' and not ignore_hashes_set:
               excluded_pairs.append(pair) 
               continue

            file_set.add(pair)

    return file_set


def main():
    parser = argparse.ArgumentParser(description='Compare two md5deep file listing files') 
    parser.add_argument('file1',metavar='file1',
                        help='md5deep file listing file 1')
    parser.add_argument('file2',metavar='file2',
                        help='md5deep file listing file 2')
    parser.add_argument('-c', metavar='num', type=int, choices=[1, 2],
                        help='copy diff of files in a given direction (1 or 2)')
    parser.add_argument('--ignore-hashes',action='store_true',
                        help='don\'t compare hashes')
    parser.add_argument('--ignore-paths',action='store_true',
                        help='don\'t compare filepaths')
    parser.add_argument('--exclude-path-list', nargs='+', metavar='pattern',
                        help='list of regexes where if a filepath matches any of them it is not included in the comparisons.')
    parser.add_argument('--include-path-list', nargs='+', metavar='pattern',
                        help='list of regexes where a filepath must match at least one to be included in the comparisons.')
    args = parser.parse_args()

    date = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    console_handler = logging.StreamHandler()
    logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(message)s',
                        level=logging.DEBUG,
                        handlers=[console_handler])

    if args.ignore_paths and args.ignore_hashes:
        print('Both the --ignore-paths and --ignore-hashes paths can\'t simultaneously be set or nothing will be compared') 
        sys.exit(1)

    if args.exclude_path_list and args.include_path_list:
        print('Both the --include-path-list and --exclude-path-list can\'t simultaneously be set. Either set one or the other or none.')

    file1_pair_exclusion_list = [] # This variable tracks the number of files in file 1 who's hash is all asterisks (these hashes are created by openrvdas when it doesn't want to generate hash for a large file.
    file2_pair_exclusion_list = []
   
    set1 = process_file(args.file1, file1_pair_exclusion_list, args.ignore_hashes, args.exclude_path_list, args.include_path_list)
    set2 = process_file(args.file2, file2_pair_exclusion_list, args.ignore_hashes, args.exclude_path_list, args.include_path_list)

    print("\n--------------BEGIN VERIFY_MD5DEEP REPORT-------------\n")

    #if len(set1) == len(set2) and set1 == set2:
    #    print(f'{args.file1} and {args.file2} are the same.')
    #else:
    unique_to_set1, unique_to_set2 = subtract_sets_with_similar_paths(set1, set2, args.ignore_hashes, args.ignore_paths)
    # If the user hasn't specified that they want only file 2 results shown then display file 1 results.
    if args.c != 2:
        for count, item in enumerate(unique_to_set2, 1):
            print(f'pair #{count} missing from {args.file1}: {item}')
        if len(unique_to_set2) == 0:
            print(f'{args.file1} is not missing any files from {args.file2}.')

    if not args.c:
        print(f'\n---------------------------------------------------\n')

    # If the user hasn't specified that they want only file 1 results shown then display file 2 results.
    if args.c != 1:
        for count, item in enumerate(unique_to_set1, 1):
            print(f'pair #{count} missing from {args.file2}: {item}')
        if len(unique_to_set1) == 0:
            print(f'{args.file2} is not missing any files from {args.file1}.')

    print("\n----------------------FINAL TALLY----------------------\n")

    if args.c != 2:
        print(f'{args.file1} contains {len(set1)} files and is missing {len(unique_to_set2)} of the {len(set2)} file(s) that {args.file2} has.') 

    if args.c != 1:
        print(f'{args.file2} contains {len(set2)} files and is missing {len(unique_to_set1)} of the {len(set1)} file(s) that {args.file1} has.')

    print("\n----------------------NOTES----------------------\n")
    
    if args.ignore_hashes:
        print(f'Note: hash values were not compared.')

    if args.ignore_paths:
        print(f'Note: filepaths were not compared.')

    if len(file1_pair_exclusion_list) > 0:
        print(f'Note: {args.file1} contains {len(file1_pair_exclusion_list)} file(s) that weren\'t compared either because they had an all-asterisk hash value or they matched an exclusion list.')

    if len(file2_pair_exclusion_list) > 0:
        print(f'Note: {args.file2} contains {len(file2_pair_exclusion_list)} file(s) that weren\'t compared either because they had an all-asterisk hash value or they matched an exclusion list.')

if __name__ == "__main__":
    main()

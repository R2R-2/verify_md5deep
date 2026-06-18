#!/usr/bin/env python3

from verify_md5deep_helper_functions import *
import argparse
import os
import shutil
from pathlib import Path
import datetime
import logging
import re
import sys


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
    try:
        with open(file_name, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                split_1 = line.split(',') # This variable be a list of substrings of the line separated by commas (not including the commas).
                split_2 = line.split() # This variable is useful for manifest files that contain only two columns (hash, filepath) separated by a space or multiple spaces.

                # This is the regular md5deep format that you get by running the md5deep command.
                if len(split_1) == 4:
                    hashval = split_1[1].strip()
                    pathval = split_1[3].strip()
                    pair = (hashval, pathval)

                # Distros in the OpenVDM/OpenRVDAS format will have an md5deep file called
                # "md5_summary.txt" and these are different because they don't only have 2 columns.
                elif len(split_2) == 4:  # WHOI space-delimited format (4 columns)
                    hashval = split_2[1].strip()
                    pathval = split_2[3].strip()
                    pair = (hashval, pathval)
                    if is_valid_file_hash(hashval) and is_valid_file_path(pathval):
                        pair = (hashval, pathval)
                    # The below case handles an edge case where a md5_summary.txt file is being read with a path that contains spaces. 
                    # In this case you must join the path together because otherwise the hash value becomes part of the path instead
                    # of a hash (and obviously the path gets cut off).
                    elif is_valid_file_hash(split_2[0].strip()) and is_valid_file_path(" ".join(split_2[1:]).strip()):
                        pair = (split_2[0].strip(), " ".join(split_2[1:]))

                elif len(split_2) == 2:
                    hashval = split_2[0].strip()
                    pathval = split_2[1].strip()
                    pair = (hashval, pathval)

                # edu.washington md5deep format:
                # 3 columns: file size, hash, absolute path (comma-delimited)
                elif len(split_1) == 3:
                    hashval = split_1[1].strip()
                    pathval = split_1[2].strip()
                    pair = (hashval, pathval)

                # Unrecognized manifest format
                else:
                    continue


                # Exclude pairs with hash values equal to the long string of asterisks hashes unless the user has elected not to compare hashes.
                if pair[0] == '********************************' and not ignore_hashes_set:
                   excluded_pairs.append((pair, "the hash is all asterisks (and we aren't ignoring hashes)")) 
                   continue

                #### This section looks to exclude the pair for any reason. If a pair matches any of these conditionals it will be excluded from comparison and will instead be recorded in a list along with its reason for being excluded.
                if exclude_path_list:
                    # Check if any regex pattern in the list matches the path (pair[1])
                    if any(re.search(pattern, pair[1]) for pattern in exclude_path_list):
                        excluded_pairs.append((pair, "the path matched a pattern in an exclude_path_list"))
                        continue

                if include_path_list:
                    # Check if the path is included in the include_path_list regex. If not then don't add the pair for consideration.
                    if not (any(re.search(pattern, pair[1]) for pattern in include_path_list)):
                        excluded_pairs.append((pair, "the path did not match a pattern in the include_path_list"))
                        continue

                if not is_valid_file_hash(pair[0]):
                    # Check the hash value if a valid hash. If not, then exclude pair:
                    excluded_pairs.append((pair, "the hash value is invalid"))
                    continue

                if not is_valid_file_path(pair[1]):
                    excluded_pairs.append((pair, "the path is invalid"))
                    continue


                file_set.add(pair)

    except FileNotFoundError:
        logging.error(f"File not found: {file_name}")
        sys.exit(1)
    except PermissionError:
        logging.error(f"Permission denied: {file_name}")
        sys.exit(1)

    return file_set


def main():
    parser = argparse.ArgumentParser(description='Compare two md5deep file listing files') 
    parser.add_argument('file1',metavar='file1',
                        help='md5deep file listing file 1')
    parser.add_argument('file2',metavar='file2',
                        help='md5deep file listing file 2')
    parser.add_argument('-c', metavar='num', type=int, choices=[1, 2],
                        help='copy diff of files in a given direction (1 or 2)')
    parser.add_argument('-s', '--show-summary', action='store_true', dest='show_summary', help='output only the summary not individual diffed files. The summary will not show excluded_files')
    parser.add_argument('-o', '--output-filepath', dest='output_filepath', help='write a copy of the output to a file')
    parser.add_argument('--ignore-hashes',action='store_true',
                        help='don\'t compare hashes')
    parser.add_argument('--ignore-paths',action='store_true',
                        help='don\'t compare filepaths')
    parser.add_argument('--exclude-path-list', nargs='+', metavar='pattern',
                        help='list of regexes where if a filepath matches any of them it is not included in the comparisons')
    parser.add_argument('--include-path-list', nargs='+', metavar='pattern',
                        help='list of regexes where a filepath must match at least one to be included in the comparisons')
    parser.add_argument('--show-excluded-pairs',action='store_true',
                        help='show all of the pairs that were not compared along with their reason for exclusion')
    args = parser.parse_args()

    date = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    console_handler = logging.StreamHandler()
    logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(message)s',
                        level=logging.DEBUG,
                        handlers=[console_handler])

    if args.ignore_paths and args.ignore_hashes:
        output_file.write('Both the --ignore-paths and --ignore-hashes paths can\'t simultaneously be set or nothing will be compared') 
        sys.exit(1)

    if args.exclude_path_list and args.include_path_list:
        output_file.write('Both the --include-path-list and --exclude-path-list can\'t simultaneously be set. Either set one or the other or none.')

    # Validate the path if provided
    if args.output_filepath:
        check_writable(args.output_filepath)
        output_file = Tee(args.output_filepath)
        sys.stdout = output_file
    else:
        output_file = TerminalOnly()

    file1_pair_exclusion_list = [] # This variable tracks the number of files in file 1 who's hash is all asterisks (these hashes are created by openrvdas when it doesn't want to generate hash for a large file.
    file2_pair_exclusion_list = []
   
    set1 = process_file(args.file1, file1_pair_exclusion_list, args.ignore_hashes, args.exclude_path_list, args.include_path_list)
    set2 = process_file(args.file2, file2_pair_exclusion_list, args.ignore_hashes, args.exclude_path_list, args.include_path_list)

    output_file.write("\n--------------BEGIN VERIFY_MD5DEEP REPORT-------------\n")

    #if len(set1) == len(set2) and set1 == set2:
    #    output_file.write(f'{args.file1} and {args.file2} are the same.')
    #else:
    unique_to_set1, unique_to_set2 = subtract_sets_with_similar_paths(set1, set2, args.ignore_hashes, args.ignore_paths)
    if args.show_excluded_pairs:
        output_file.write("--------------EXCLUDED PAIRS (shown because --excluded-pairs flag set)--------------\n\n", args.show_summary)
        for pair in file1_pair_exclusion_list:
            output_file.write(str(pair[0]) + "\n", args.show_summary)
            #if args.output_filepath:
            #    Path(args.output_filepath).write_text(str(pair[0]) + "\n")
        for pair in file2_pair_exclusion_list:
            output_file.write(str(pair[0]) + "\n", args.show_summary)
            #if args.output_filepath:
            #    Path(args.output_filepath).write_text(str(pair[0]) + "\n")
        output_file.write("\n--------------END EXCLUDE PAIRS SECTION--------------\n", args.show_summary)

    # If the user hasn't specified that they want only file 2 results shown then display file 1 results.
    if args.c != 2:
        for count, item in enumerate(unique_to_set2, 1):
            output_file.write(f'\npair #{count} missing from {args.file1}: {item}', args.show_summary)
        if len(unique_to_set2) == 0:
            output_file.write(f'\n{args.file1} is not missing any files from {args.file2}.', args.show_summary)
        output_file.write("\n", args.show_summary)

    if not args.c:
        output_file.write(f'\n---------------------------------------------------\n', args.show_summary)

    # If the user hasn't specified that they want only file 1 results shown then display file 2 results.
    if args.c != 1:
        for count, item in enumerate(unique_to_set1, 1):
            output_file.write(f'\npair #{count} missing from {args.file2}: {item}', args.show_summary)
        if len(unique_to_set1) == 0:
            output_file.write(f'\n{args.file2} is not missing any files from {args.file1}.', args.show_summary)
        output_file.write("\n", args.show_summary)

    output_file.write("\n----------------------FINAL TALLY----------------------")

    if args.c != 2:
        output_file.write(f'\n{args.file1} contains {len(set1)} files and is missing {len(unique_to_set2)} of the {len(set2)} valid file(s) ({len(set2) + len(file2_pair_exclusion_list)} files total) that {args.file2} has.') 

    if args.c != 1:
        output_file.write(f'\n{args.file2} contains {len(set2)} files and is missing {len(unique_to_set1)} of the {len(set1)} valid file(s) ({len(set1) + len(file1_pair_exclusion_list)} files total) that {args.file1} has.')

    output_file.write("\n\n----------------------NOTES----------------------\n")
    
    if args.ignore_hashes:
        output_file.write(f'\nNote: hash values were not compared.')

    if args.ignore_paths:
        output_file.write(f'\nNote: filepaths were not compared.')

    if len(file1_pair_exclusion_list) > 0:
        output_file.write(f'\nNote: {args.file1} contains {len(file1_pair_exclusion_list)} file(s) that weren\'t compared because they either had an invalid hash value, invalid file path, or matched an exclusion list.')

    if len(file2_pair_exclusion_list) > 0:
        output_file.write(f'\nNote: {args.file2} contains {len(file2_pair_exclusion_list)} file(s) that weren\'t compared because they either had an invalid hash value, invalid file path, or matched an exclusion list.')

    output_file.write("\n--------------END OF VERIFY_MD5DEEP REPORT-------------\n")

if __name__ == "__main__":
    main()

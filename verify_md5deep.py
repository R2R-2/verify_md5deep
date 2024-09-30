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


def subtract_sets_with_similar_paths(set1, set2, cutoff_percentage=0.4):
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
            if hash1 == hash2 and are_paths_similar(path1, path2, cutoff_percentage):
                return True
        return False

    # Find items in set1 that are not in set2
    unique_to_set1 = {item for item in set1 if not find_similar_or_exact(item, set2)}

    # Find items in set2 that are not in set1
    unique_to_set2 = {item for item in set2 if not find_similar_or_exact(item, set1)}

    return unique_to_set1, unique_to_set2


def process_file(file_name, hash_only, path_only):
    file_set = set()
    with open(file_name) as f:
        for line in f:
            split_1 = line.split(',') # This variable be a list of substrings of the line separated by commas (not including the commas).
            split_2 = line.split(' ') # This variable is useful for manifest files that contain only two columns (hash, filepath) separated by a space.

            # Determine which format of md5deep file we are dealing with and construct (hash, filepath) pairs for each line accordingly.
            # This is the regular md5deep format that you get by running the md5deep command. 
            if len(split_1) == 4:
                pair = (split_1[1].strip(), split_1[3].strip())
            # Distros in the OpenVDM/OpenRVDAS format will have an md5deep file called "md5_summary.txt"
            # and these are different because they don't only have 2 columns.
            elif len(split_2) == 2:
                pair = (split_2[0].strip(), split_2[1].strip())
            else:
                # If we've not found either 2 or 4 commas then I don't recognize this manifest file so just skip this line.
                continue

            # If the user has elected to not check paths then set the path part of the pair to the same thing for all pairs.
            if hash_only:
                pair = (pair[0], "ignore me")

            # In a similar fashion if the user has specified to not check hashes then replace all hashes with a constant so that they'll all match.
            if path_only:
                pair = ("ignore me", pair[1])
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
    parser.add_argument('-f',action='store_true',
                        help='only compare hashes')
    parser.add_argument('-q',action='store_true',
                        help='only compare filepaths')
    args = parser.parse_args()

    date = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    console_handler = logging.StreamHandler()
    logging.basicConfig(format='%(asctime)s - %(levelname)-8s - %(message)s',
                        level=logging.DEBUG,
                        handlers=[console_handler])
    
    set1 = process_file(args.file1, args.f, args.q)
    set2 = process_file(args.file2, args.f, args.q)

    if len(set1) == len(set2) and set1 == set2:
        logging.info('File 1 and file 2 are the same')
    else:
        unique_to_set1, unique_to_set2 = subtract_sets_with_similar_paths(set1, set2)
        if args.a:
            for item in unique_to_set1:
                logging.info(f'FILE THAT IS IN FILE 1 AND NOT IN FILE 2: {item}')

            for item in unique_to_set2:
                logging.info(f'FILE THAT IS IN FILE 2 AND NOT IN FILE 1: {item}')
        logging.info(f'File 1 contains {len(set1)} files and has {len(unique_to_set1)} files that file 2 does not (1 - 2)')
        logging.info(f'File 2 contains {len(set2)} files and has {len(unique_to_set2)} files that file 1 does not (2 - 1)')

        """
   else:
        if args.a:
            for item in set1 - set2:
                logging.info(f'FILE THAT IS IN FILE 1 AND NOT IN FILE 2: {item}')
            for item in set2 - set1:
                logging.info(f'FILE THAT IS IN FILE 2 AND NOT IN FILE 1: {item}')
        logging.info(f'File 1 contains {len(set1)} files and has {len(set1 - set2)} files that file 2 does not (1 - 2)')
        logging.info(f'File 2 contains {len(set2)} files and has {len(set2 - set1)} files that file 1 does not (2 - 1)')
    """
    
    if args.c:
        if args.c[0] == '2':
            copy_difference(args.file2, set2 - set1)
        elif args.c[0] == '1':
            copy_difference(args.file1, set1 - set2)
        else:
            logging.error('Invalid arguments for copying (must be 1 or 2)')


if __name__ == "__main__":
    main()

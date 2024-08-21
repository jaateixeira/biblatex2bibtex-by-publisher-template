#!/usr/bin/env python3
# By Jose Teixeira <jose.teixeira@abo.fi>

# Based on work from fmatter 
# https://github.com/fmatter/biblatex2bibtex.git 
# Add pre UTF8 filter 

# Example of usage

# biblatex2bibtex-by-publisher-template.py *bib -o curated-references.bib



import argparse
import logging
import os
import sys
from pathlib import Path
import re
import subprocess
import bibtexparser
import colorlog

from pybtex.database.input import bibtex
from pybtex.database import parse_file, BibliographyData, Entry


# For the progress bar 
from rich.progress import track

# To create a beautiful report for any Python object, including a string.
from rich import inspect

# for debugging in just one line the fuctions 
from rich.console import Console
console = Console()

# Using Rich Automatic Traceback Handler
from rich.traceback import install
install(show_locals=True)


handler = colorlog.StreamHandler(None)
handler.setFormatter(
    colorlog.ColoredFormatter("%(log_color)s%(levelname)-7s%(reset)s %(message)s")
)
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.propagate = True
log.addHandler(handler)


__author__ = "Florian Matter"
__email__ = "fmatter@mailbox.org"
__version__ = "0.0.5.dev"

macro_expr = re.compile(r"\\.*?\{(?P<content>.*?)\}")


# Checks if file_path is a valid UTF-8 file 
def is_valid_utf8(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='strict') as f:
            # Read the entire file to check for encoding errors
            f.read()
        return True
    except UnicodeDecodeError:
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def remove_macros(s):
    return s
    #return macro_expr.sub(r"\g<content>", s)


def preprocess(biblatex_file):

    console.log(biblatex_file,log_locals=True)
    
    print (f"\n \t Pre-processing {biblatex_file}")
    
    biblatex_file = Path(biblatex_file)
    bib_data = bibtex.Parser().parse_file(biblatex_file)
    
    for entry in bib_data.entries.values():
        if entry.type == "collection":
            print ("\n \t Should booktitles be title !!")
            entry.fields["booktitle"] = entry.fields["title"]
    temp_file = (
        biblatex_file.parent / f"{biblatex_file.stem}_tmp{biblatex_file.suffix}"
    )
    bib_data.to_file(temp_file)

    with open(temp_file, "r", encoding="utf-8") as f:
        content = remove_macros(f.read())
        
    with open(temp_file, "w", encoding="utf-8") as f:
        f.write(content)

    if os.path.isfile(args.configfile):
        conf_file= args.configfile
        print (f"\n Using configfile={conf_file}")
    else:
        print ("ERROR: Invalid configuration file")
        sys.exit()

    

    print()
    print("Running:")
    print(f"biber --tool --configfile={conf_file} --output-resolve --output-file='{temp_file}' {temp_file}")
    #print(f"biber --tool  --output-resolve --output-file='{temp_file}' {temp_file}")
    print()
    
    subprocess.run(
        f"biber --tool --configfile={conf_file} --output-resolve --output-file='{temp_file}' {temp_file}",
        #f"biber --tool --output-resolve --output-file='{temp_file}' {temp_file}",
        shell=True,
        check=True,
    )
    Path(f"{temp_file}.blg").unlink()
    return temp_file


def modify(temp_file):

    console.log(f'Modifying {temp_file=}',log_locals=True)


    #print(inspect(bibtexparser, methods=True))
    #sys.exit()
    
    with open(temp_file, "r", encoding="utf-8") as bibtex_file:
        #bib_database = bibtexparser.load(bibtex_file)
        print(f"\n parsing {temp_file}\n")
        bib_database = bibtexparser.parse_file(temp_file)


    for entry in bib_database.entries:

        trash, entry_type = entry.items()[0]
        
        if args.verbose:
            print(f"\n \t Modfifying entry={entry}")
            print(f"\n \t entry_type={entry_type}")
            
        # For bibtex entries with TITLE instead of title 
        try:
            tmp = entry['title']
        except KeyError:
            if entry_type == 'book':
                entry['title']=entry['booktitle']
            elif entry_type == 'inbook':
                entry['title']=entry['chapter']
            elif 'TITLE' in entry:
                entry['title']=entry['TITLE']
            else:
                print ("ERROR can't figure why a key is missing from entry={entry}")
                sys.exit()



            
        entry["title"] = entry["title"].replace("{", "").replace("}", "") 
        
        if "booktitle" in entry:
            entry["booktitle"] = entry["booktitle"].replace("{", "").replace("}", "")
        if "pages" in entry:
            entry["pages"] = entry["pages"].replace("--", "–")
        replace = {
            "date": "year",
            "location": "address",
            "journaltitle": "journal",
            "issue": "number",
            "origdate": "year",
            "school": "institution",
            "maintitle": "booktitle",
        }
        for k, v in replace.items():
            if k in entry:
                entry[v] = entry[k]
                del entry[k]
        if "year" in entry and "-" in entry["year"]:
            entry["year"] = entry["year"].split("-")[0]
        if "note" in entry and entry["note"] == "\\textsc{ms}":
            del entry["note"]
            entry["howpublished"] = "Manuscript"
    temp_file.unlink()
    return bib_database






def append_string_to_file(string_to_append,file_path):
    """
    Append a string to a file.

    :param file_path: Path to the file to append to
    :param string_to_append: The string to append to the file
    """
    try:
        with open(file_path, 'a') as file:
            file.write(string_to_append)
            file.write('\n')  # Optional: Add a newline after the appended string
    except Exception as e:
        print(f"An error occurred: {e}")


def convert(biblatex_files, bibtex_output):

    console.log(biblatex_files,bibtex_output,log_locals=True)
    
    temp_files = []
    for biblatex_file in track(biblatex_files):
        temp_files.append(preprocess(biblatex_file))

    databases = []
    for temp_file in temp_files:
        databases.append(modify(temp_file))

    with open(bibtex_output, "w", encoding="utf-8") as bibtex_file:
        for database in databases:
            if args.verbose:
                print(f"\nWant to dump databasse:")
                print(f"database={database}")
                #print(bibtexparser.write_string(database))                
            #bibtexparser.dump(database, bibtex_file)
            #append_to_bibtex_file(database, bibtex_output)
            append_string_to_file(bibtexparser.write_string(database),bibtex_output)                

            print(f"Contents of bibtexparser {database} appended to bibtex_output={bibtex_output}")

        

    
parser = argparse.ArgumentParser(description="convert biblatex to bibtex files")
parser.add_argument(
        "biblatexfiles", nargs="+", help="biblatex file(s) to be converted", type=str
    )
parser.add_argument("-o",
        "--output", nargs="?", help="bibtex output file", type=str, default="curated-references.bib"
    )


parser.add_argument("-c",
        "--configfile", nargs="?", help="biber tool configuration file", type=str, default="./bin/biblatex2bibtex-by-publisher-template/data/biblatex2bibtex.conf"
    )



parser.add_argument("-t",'--publisher-template', choices=['non-strict', 'Wiley-NJDv5', 'Wiley-book','Springer-sn-jnl', 'Springer-LNCS','IEEE-tran','ACM-acmart','Elsevier-elsarticle','Sage-sagej'], default="non-strict", nargs='?',type=str, help="the publisher template style  according to the output .bib file should be formatted")

parser.add_argument('-v', '--verbose', action="count", 
                        help="increase output verbosity (e.g., -vv is more than -v)")

args = parser.parse_args()


#print(inspect(args.biblatexfiles,methods=True))

print (f"Iterating over {len(args.biblatexfiles)} bibtex files:\n")

for filename in args.biblatexfiles:
    print(f"\t{filename}")

print("")

for filename in args.biblatexfiles:
    in_file = Path(filename)
    if not in_file.is_file() or in_file.suffix != ".bib":
        print("Please enter a path to a .bib file")
        sys.exit()

    if not is_valid_utf8(in_file):
        print(f"The file{in_file} is not a valid utf-8 encoded file")
        sys.exit()
        
    if args.output is None:
        out_file = Path(in_file.parent / f"{in_file.stem}_bibtex{in_file.suffix}")
        print(f"No bibtex output specified, saving to {out_file}")
    else:
        out_file = Path(args.output)

    convert(args.biblatexfiles, out_file)


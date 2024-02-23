from pathlib import Path


def run(input_file: Path, output_file: Path) -> None:
    code_map = {
        "N": "scientific name",
        "C": "common name",
        "S": "synonym"
    }
    with input_file.open() as f, output_file.open("w") as of:
        of.write("tax_id\tcode\tkingdom\t"
                 "scientific name\tcommon name\tsynonym\n")
        curr_organism = {}
        organism_section = False
        for i, line in enumerate(f):
            if not organism_section and line.startswith("_____"):
                organism_section = True
                continue
            if not organism_section:
                continue
            if line.startswith("----------"):
                break
            if line.startswith("============"):
                break
            if line.startswith("("):
                break
            if line.strip():
                if line[0] == " ":
                    code, name = line.strip().split("=")
                    curr_organism[code_map[code]] = name
                else:
                    if curr_organism:
                        of.write(f"{curr_organism['tax_id']}\t")
                        of.write(f"{curr_organism['code']}\t")
                        of.write(f"{curr_organism['kingdom']}\t")
                        of.write(f"{curr_organism['scientific name']}\t")
                        of.write(f"{curr_organism.get('common name', '')}\t")
                        of.write(f"{curr_organism.get('synonym', '')}\n")
                    code, kdom, taxon, sname = line.strip().split(maxsplit=3)
                    curr_organism["code"] = code
                    curr_organism["kingdom"] = kdom
                    curr_organism["tax_id"] = taxon[:-1]
                    code, name = sname.split("=")
                    curr_organism[code_map[code]] = name
        if curr_organism:
            of.write(f"{curr_organism['tax_id']}\t")
            of.write(f"{curr_organism['code']}\t")
            of.write(f"{curr_organism['kingdom']}\t")
            of.write(f"{curr_organism['scientific name']}\t")
            of.write(f"{curr_organism.get('common name', '')}\t")
            of.write(f"{curr_organism.get('synonym', '')}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        description="Parser for UniProtKB's speclist.txt")
    parser.add_argument("-i", "--input-file", required=True,
                        help="Path to the speclist.txt file")
    parser.add_argument("-o", "--output-file", required=True,
                        help="Path to a TSV file")
    args = parser.parse_args()
    run(Path(args.input_file),
        Path(args.output_file),)

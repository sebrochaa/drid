import requests


PUBCHEM_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def search_pubchem(drug_name):

    url = (
        f"{PUBCHEM_URL}/compound/name/"
        f"{drug_name}/property/"
        "MolecularFormula,MolecularWeight,CanonicalSMILES,IsomericSMILES/"
        "JSON"
    )

    response = requests.get(
        url,
        timeout=30
    )

    if response.status_code == 404:
        print(f"No PubChem record found for: {drug_name}")
        return None

    response.raise_for_status()

    data = response.json()

    properties = data["PropertyTable"]["Properties"][0]

    return properties


def main():

    drug_name = input(
        "Enter a drug name: "
    ).strip()

    if not drug_name:
        print("Please enter a drug name.")
        return

    print()
    print(
        f"Searching PubChem for {drug_name}..."
    )
    print()

    result = search_pubchem(drug_name)

    if result is None:
        return

    print("--------------------------------------")

    print(
        f"PubChem CID: "
        f"{result.get('CID', 'N/A')}"
    )

    print(
        f"Molecular formula: "
        f"{result.get('MolecularFormula', 'N/A')}"
    )

    print(
        f"Molecular weight: "
        f"{result.get('MolecularWeight', 'N/A')}"
    )

    print(
        f"Canonical SMILES: "
        f"{result.get('ConnectivitySMILES', 'N/A')}"
    )

    print(
        f"Isomeric SMILES: "
        f"{result.get('SMILES', 'N/A')}"
    )

    print("--------------------------------------")


if __name__ == "__main__":
    main()
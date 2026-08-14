import requests


CLINICAL_TRIALS_URL = (
    "https://clinicaltrials.gov/api/v2/studies"
)


def search_trials(drug_name, limit=10):

    params = {
        "query.term": drug_name,
        "pageSize": limit,
        "format": "json"
    }

    response = requests.get(
        CLINICAL_TRIALS_URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


def main():

    drug_name = input(
        "Enter a drug name: "
    ).strip()


    if not drug_name:

        print("Please enter a drug name.")

        return


    print()
    print(
        f"Searching ClinicalTrials.gov for {drug_name}..."
    )
    print()


    data = search_trials(
        drug_name
    )


    studies = data.get(
        "studies",
        []
    )


    print(
        f"Studies found: {len(studies)}"
    )

    print()


    for study in studies:

        protocol = study.get(
            "protocolSection",
            {}
        )


        identification = protocol.get(
            "identificationModule",
            {}
        )


        status = protocol.get(
            "statusModule",
            {}
        )


        design = protocol.get(
            "designModule",
            {}
        )


        conditions = protocol.get(
            "conditionsModule",
            {}
        )


        study_id = identification.get(
            "nctId",
            "Unknown"
        )


        title = identification.get(
            "briefTitle",
            "Unknown"
        )


        overall_status = status.get(
            "overallStatus",
            "Unknown"
        )


        phases = design.get(
            "phases",
            []
        )


        study_conditions = conditions.get(
            "conditions",
            []
        )


        print("--------------------------------------")

        print(
            f"Study: {study_id}"
        )

        print(
            f"Title: {title}"
        )

        print(
            f"Status: {overall_status}"
        )

        print(
            f"Phase: {', '.join(phases) if phases else 'N/A'}"
        )

        print(
            "Conditions: "
            + (
                ", ".join(study_conditions)
                if study_conditions
                else "N/A"
            )
        )


    print("--------------------------------------")


if __name__ == "__main__":

    main()
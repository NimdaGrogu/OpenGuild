

if __name__ =="__main__":

    import pandas as pd

    # Load your CSV
    df = pd.read_csv("../job_tracker.csv")

    # Add new column with constant value
    df["CandidateName"] = "jonathan"

    # Save back (optional)
    df.to_csv("../job_tracker.csv", index=False)

    print(df.head())











from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from load_data import load_nhanes_data


RANDOM_STATE = 42
TEST_SIZE = 0.20

FEATURES = ["age", "sex", "bmi"]
TARGET = "diabetes"


def prepare_data():
    data = load_nhanes_data()

    X = data[FEATURES]
    y = data[TARGET]

    return train_test_split(
        X,
        y,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y,
    )


def build_model():
    return Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "classifier",
                LogisticRegression(
                    random_state=RANDOM_STATE,
                    max_iter=1000,
                ),
            ),
        ]
    )


def calculate_metrics(y_true, probabilities):
    predictions = (probabilities >= 0.5).astype(int)

    auroc = roc_auc_score(y_true, probabilities)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1],
    ).ravel()

    sensitivity = tp / (tp + fn)
    specificity = tn / (tn + fp)

    return auroc, sensitivity, specificity


def main():
    X_train, X_test, y_train, y_test = prepare_data()

    model = build_model()
    model.fit(X_train, y_train)

    probabilities = model.predict_proba(X_test)[:, 1]

    auroc, sensitivity, specificity = calculate_metrics(
        y_test,
        probabilities,
    )

    print("NHANES Diabetes Baseline")
    print("-------------------------")
    print(f"Training rows: {len(X_train)}")
    print(f"Test rows: {len(X_test)}")
    print(f"Random state: {RANDOM_STATE}")
    print(f"AUROC: {auroc:.4f}")
    print(f"Sensitivity: {sensitivity:.4f}")
    print(f"Specificity: {specificity:.4f}")


if __name__ == "__main__":
    main()
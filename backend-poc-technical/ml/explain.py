import shap

from train_baseline import FEATURES, build_model, prepare_data


def main():
    X_train, X_test, y_train, y_test = prepare_data()

    model = build_model()
    model.fit(X_train, y_train)

    scaler = model.named_steps["scaler"]
    classifier = model.named_steps["classifier"]

    X_train_scaled = scaler.transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    explainer = shap.LinearExplainer(
        classifier,
        X_train_scaled,
    )

    patient_index = 0
    patient = X_test.iloc[patient_index]
    patient_scaled = X_test_scaled[patient_index:patient_index + 1]

    shap_values = explainer.shap_values(patient_scaled)

    probability = model.predict_proba(
        X_test.iloc[[patient_index]]
    )[0, 1]

    print("SHAP Explanation for One Held-Out Patient")
    print("-----------------------------------------")
    print()
    print("Patient values:")

    for feature in FEATURES:
        print(f"{feature}: {patient[feature]}")

    print()
    print(f"Predicted diabetes probability: {probability:.4f}")
    print()
    print("SHAP values:")

    for feature, value in zip(FEATURES, shap_values[0]):
        direction = "raises" if value > 0 else "lowers"

        print(
            f"{feature}: {value:.4f} "
            f"({direction} model output)"
        )


if __name__ == "__main__":
    main()
"""
BASILICA — Intent Classifier Training
Milestone 4: Model Development & Training

Architecture: TF-IDF vectorizer + Logistic Regression
Why this and not a deep learning model: with only ~200 labeled examples across
9 intents, a Transformer/deep model would badly overfit. TF-IDF + Logistic
Regression is the standard, defensible baseline for small-data text
classification — fast to train, easy to explain to a supervisor, and strong
enough for a well-scoped FAQ chatbot.
"""

import re
import json
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

def clean_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s?']", "", text)
    text = re.sub(r"\s+", " ", text)
    return text

def main():
    train_df = pd.read_csv("train.csv")
    val_df = pd.read_csv("val.csv")
    test_df = pd.read_csv("test.csv")

    X_train, y_train = train_df["text_clean"], train_df["intent"]
    X_val, y_val = val_df["text_clean"], val_df["intent"]
    X_test, y_test = test_df["text_clean"], test_df["intent"]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_val_vec = vectorizer.transform(X_val)
    X_test_vec = vectorizer.transform(X_test)

    param_grid = {"C": [0.1, 1, 5, 10, 20]}
    grid = GridSearchCV(
        LogisticRegression(max_iter=1000),
        param_grid,
        cv=3,
        scoring="f1_macro",
    )
    grid.fit(X_train_vec, y_train)
    best_model = grid.best_estimator_
    print(f"Best hyperparameter: C = {grid.best_params_['C']}")

    val_preds = best_model.predict(X_val_vec)
    print(f"\nValidation accuracy: {accuracy_score(y_val, val_preds):.3f}")
    print(f"Validation F1 (macro): {f1_score(y_val, val_preds, average='macro'):.3f}")

    test_preds = best_model.predict(X_test_vec)
    test_acc = accuracy_score(y_test, test_preds)
    test_f1 = f1_score(y_test, test_preds, average="macro")
    print(f"\n=== FINAL TEST SET RESULTS (never seen during training/tuning) ===")
    print(f"Test accuracy: {test_acc:.3f}")
    print(f"Test F1 (macro): {test_f1:.3f}")
    print(f"\nClassification report:\n{classification_report(y_test, test_preds)}")

    CONFIDENCE_THRESHOLD = 0.80  # below this, the chatbot falls back to "contact parish office"

    results = {
        "best_C": grid.best_params_["C"],
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "validation_accuracy": round(accuracy_score(y_val, val_preds), 4),
        "validation_f1_macro": round(f1_score(y_val, val_preds, average="macro"), 4),
        "test_accuracy": round(test_acc, 4),
        "test_f1_macro": round(test_f1, 4),
        "classification_report": classification_report(y_test, test_preds, output_dict=True),
    }
    with open("evaluation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    joblib.dump(best_model, "intent_classifier_v1.joblib")
    joblib.dump(vectorizer, "tfidf_vectorizer_v1.joblib")
    print(f"\nSaved: intent_classifier_v1.joblib, tfidf_vectorizer_v1.joblib, evaluation_results.json")

    if test_acc >= 0.85:
        print(f"\n✅ Meets Milestone 1 objective: test accuracy {test_acc:.1%} >= 85% target")
    else:
        print(f"\n⚠️  Below 85% target ({test_acc:.1%}) — consider adding more training examples")

if __name__ == "__main__":
    main()
import json
from pathlib import Path
from waste_category_trainer import train_waste_classifier, categorize_waste
from ai_engine import get_ai_response


def main():
    print("Training waste classification model...")
    model = train_waste_classifier(force=True)
    print("Model type:", model.get("type"))
    print("Saved model path:", Path(__file__).resolve().parent / "waste_classifier_model.json")

    sample_queries = [
        "Where should I put a plastic bottle?",
        "What category is an old mobile phone?",
        "How do carbon credits work for waste?",
        "Tell me about hazardous waste disposal"
    ]

    print("\nSample predictions:")
    for query in sample_queries:
        category, confidence = categorize_waste(query)
        print(f"- {query} -> {category} ({confidence}%)")

    print("\nSample AI responses:")
    for query in sample_queries:
        print(f"\nQ: {query}")
        response = get_ai_response(query)
        print(response[:1200].replace('\n', ' '))


if __name__ == "__main__":
    main()

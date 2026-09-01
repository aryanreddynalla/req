from api import detect_specialty, detect_priority


TEST_CASES = [
    (
        "My father has severe chest pain and is sweating heavily.",
        "cardiology"
    ),
    (
        "He is having a heart attack.",
        "cardiology"
    ),
    (
        "She suddenly developed slurred speech and weakness on one side.",
        "neurology"
    ),
    (
        "He had a seizure a few minutes ago.",
        "neurology"
    ),
    (
        "She has a broken arm after falling.",
        "orthopedics"
    ),
    (
        "He has severe leg pain and cannot walk.",
        "orthopedics"
    ),
    (
        "My child is seriously unwell.",
        "pediatrics"
    ),
    (
        "My baby has a high fever.",
        "pediatrics"
    ),
    (
        "There was a serious road accident with heavy bleeding.",
        "general trauma"
    ),
    (
        "He has high fever and vomiting.",
        "general care"
    )
]


def main():

    correct = 0

    print("\n108 AI EMERGENCY SPECIALTY TEST")
    print("=" * 80)

    for sentence, expected in TEST_CASES:

        predicted = detect_specialty(sentence)

        passed = predicted == expected

        if passed:
            correct += 1

        print(
            f"{'PASS' if passed else 'FAIL':<7}"
            f"{expected:<18}"
            f"{predicted:<18}"
            f"{sentence}"
        )

    total = len(TEST_CASES)

    print("=" * 80)

    print(
        f"Accuracy: {correct}/{total} "
        f"({correct / total * 100:.1f}%)"
    )


if __name__ == "__main__":
    main()
def adjust_activity_level(summary):

    score = summary.get(
        "average_activity_score",
        0
    )


    if score >= 0.8:

        return {
            "difficulty":"Medium",
            "message":
            "Patient is ready for slightly challenging activities."
        }


    elif score >=0.5:

        return {
            "difficulty":"Easy",
            "message":
            "Continue supportive recall activities."
        }


    else:

        return {
            "difficulty":"Very Easy",
            "message":
            "Use familiar memories with visual hints."
        }
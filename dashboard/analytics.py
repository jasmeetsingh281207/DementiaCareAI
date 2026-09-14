"""
Dashboard analytics engine
"""


from dashboard.reports import (
    get_performance_history
)



def activity_timeline():


    records = get_performance_history(
        limit=100
    )


    return [

        {

            "timestamp":
                record.get(
                    "timestamp"
                ),

            "activity":
                record.get(
                    "activity_type"
                ),

            "result":
                record.get(
                    "result"
                ),

            "score":
                record.get(
                    "score"
                )

        }

        for record in records

    ]



def success_rate():


    records = get_performance_history(
        limit=500
    )


    if not records:

        return 0



    successful = len(

        [

            r for r in records

            if r.get(
                "result"
            )
            ==
            "correct"

        ]

    )


    return round(

        successful /
        len(records),

        3

    )
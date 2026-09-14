import sys
import os


# =====================================================
# PROJECT PATH
# =====================================================

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


import streamlit as st


from dashboard.caregiver import (
    get_complete_caregiver_dashboard
)




# =====================================================
# PAGE CONFIG
# =====================================================


st.set_page_config(
    page_title="DementiaCareAI Caregiver",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed"
)




# =====================================================
# HEALTHCARE UI THEME
# =====================================================


st.markdown(
"""

<style>


/* ================================
GLOBAL
================================ */


.stApp {


background:

linear-gradient(
135deg,
#f0f9ff,
#ecfdf5,
#ffffff
);


font-family:

"Segoe UI",
Arial,
sans-serif;


}



header {

visibility:hidden;

}



.block-container {


max-width:1100px;

padding-top:2rem;

padding-bottom:3rem;


}




/* FORCE TEXT VISIBILITY */

p,
span,
div,
label,
.stMarkdown,
.stText {


color:#334155 !important;


}



h1 {


color:#075985 !important;

font-weight:800;


}



h2 {


color:#0369a1 !important;


}



h3 {


color:#047857 !important;


}






/* ================================
HERO
================================ */


.hero {


background:

linear-gradient(
135deg,
rgba(255,255,255,0.95),
rgba(224,242,254,0.95)
);



border-radius:32px;


padding:40px;



border:

1px solid #bae6fd;



box-shadow:

0 20px 50px rgba(14,116,144,.15);



animation:

appear 0.8s ease;


}



.hero-title {


font-size:48px;


font-weight:800;


color:#075985 !important;


}



.hero-sub {


font-size:22px;


color:#059669 !important;


margin-top:10px;


}



.hero-text {


font-size:17px;


color:#475569 !important;


line-height:1.6;


}






/* ================================
METRICS
================================ */



.metric-card {


background:

rgba(255,255,255,.9);



border-radius:24px;



padding:25px;



text-align:center;



border:

1px solid #dbeafe;



box-shadow:

0 10px 25px rgba(0,0,0,.08);



animation:

fadeUp .7s ease;


}



.metric-number {


font-size:40px;


font-weight:800;


color:#0284c7 !important;


}



.metric-label {


color:#64748b !important;


font-size:15px;


}






/* ================================
MEMORY
================================ */



.memory-card {


background:


linear-gradient(
135deg,
#ffffff,
#f0fdf4
);



border-radius:26px;



padding:25px;



margin-bottom:20px;



border-left:

7px solid #10b981;



box-shadow:

0 12px 30px rgba(0,0,0,.08);



animation:

fadeUp .8s ease;


}



.memory-card h3 {


color:#047857 !important;


}



.memory-card p {


color:#334155 !important;


}







/* ================================
ACTIVITY
================================ */



.activity-card {


background:#ffffff;



border-radius:22px;



padding:22px;



margin-bottom:18px;



border-left:

6px solid #0ea5e9;



box-shadow:

0 10px 25px rgba(0,0,0,.08);



animation:

fadeUp .8s ease;


}



.activity-card strong {


color:#075985 !important;


}



.activity-card p {


color:#334155 !important;


}





/* ================================
INSIGHTS
================================ */



.insight-card {


background:


linear-gradient(
120deg,
#ecfdf5,
#eff6ff
);



border-radius:22px;



padding:22px;



margin-bottom:15px;



border-left:

6px solid #22c55e;



box-shadow:

0 8px 25px rgba(0,0,0,.07);



}



.insight-card p {


color:#14532d !important;


}





/* ================================
PROGRESS
================================ */



.stProgress > div > div {


background:#10b981 !important;


}




/* ================================
MOBILE
================================ */



@media(max-width:700px){


.hero-title{


font-size:32px;


}



.hero{


padding:25px;


}



.metric-card{


margin-bottom:15px;


}


}





/* ================================
ANIMATION
================================ */


@keyframes fadeUp {


from{


opacity:0;


transform:
translateY(25px);


}


to{


opacity:1;


transform:
translateY(0);


}


}



@keyframes appear {


from{


opacity:0;


transform:
scale(.97);


}


to{


opacity:1;


transform:
scale(1);


}


}



</style>

""",

unsafe_allow_html=True

)






# =====================================================
# LOAD DATA
# =====================================================


dashboard = get_complete_caregiver_dashboard()


patient = dashboard["patient"]

activities = dashboard["activities"]

analytics = dashboard["analytics"]

insights = dashboard["insights"]






# =====================================================
# HERO
# =====================================================


st.markdown(
"""

<div class="hero">


<div class="hero-title">

🧠 DementiaCareAI

</div>



<div class="hero-sub">

Caregiver Memory Companion

</div>



<div class="hero-text">

A gentle digital companion helping families preserve memories,
follow daily engagement, and support meaningful conversations.

</div>



</div>


""",

unsafe_allow_html=True
)







# =====================================================
# QUICK OVERVIEW
# =====================================================


st.subheader(
"Patient Overview"
)



c1,c2,c3 = st.columns(3)



cards = [

(
patient["total_memories"],
"Memories Saved"
),


(
activities["summary"]["total_activities"],
"Memory Sessions"
),


(
f"{analytics['success_rate']*100:.0f}%",
"Engagement"
)

]



for col,data in zip(
[c1,c2,c3],
cards
):


    with col:


        st.markdown(
        f"""

        <div class="metric-card">

        <div class="metric-number">

        {data[0]}

        </div>


        <div class="metric-label">

        {data[1]}

        </div>


        </div>


        """,

        unsafe_allow_html=True
        )







# =====================================================
# MEMORY LIBRARY
# =====================================================



st.subheader(
"Personal Memory Library"
)



for memory in patient["memories"]:


    tags = ", ".join(
        memory.get("tags",[])
    )


    st.markdown(
    f"""

    <div class="memory-card">


    <h3>
    {memory["name"]}
    </h3>



    <p>
    {memory["description"]}
    </p>



    <p>

    <b>Important connections:</b>

    {tags}

    </p>



    </div>


    """,

    unsafe_allow_html=True

    )






# =====================================================
# ENGAGEMENT
# =====================================================


st.subheader(
"Memory Engagement Journey"
)



score = activities["summary"]["average_activity_score"]



st.progress(
score
)


st.write(
f"Overall engagement: {score*100:.0f}%"
)





for item in activities["recent_activity"]:


    if item["result"]=="correct":

        message = (
            "Patient remembered independently"
        )


    elif item["result"]=="partial":

        message = (
            "Patient remembered with some guidance"
        )


    else:

        message = (
            "Caregiver support was needed"
        )



    st.markdown(
    f"""

    <div class="activity-card">


    <strong>
    Memory Conversation
    </strong>



    <p>
    {message}
    </p>



    <p>

    Recall confidence:

    <b>
    {item["score"]*100:.0f}%
    </b>

    </p>



    </div>


    """,

    unsafe_allow_html=True

    )








# =====================================================
# CAREGIVER SUPPORT
# =====================================================



st.subheader(
"Caregiver Guidance"
)



for insight in insights:


    st.markdown(
    f"""

    <div class="insight-card">

    <p>

    {insight}

    </p>

    </div>


    """,

    unsafe_allow_html=True

    )







# =====================================================
# FOOTER
# =====================================================


st.divider()


st.caption(

"DementiaCareAI supports memory engagement and caregiver assistance. It is not a medical diagnosis system."

)
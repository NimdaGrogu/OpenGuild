# Markdown for the badge
sidebar_footer_style = """
<style>
/* This targets the specific container in the sidebar */
[data-testid="stSidebar"] > div:first-child {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

/* This targets the last element inside the sidebar and pushes it down */
[data-testid="stSidebar"] > div:first-child > div:last-child {
    margin-top: auto;
}
</style>
"""

buttom_style = """
        <style>
        div.stButton > button:first-child {
            border-radius: 20px;
            border: 1px solid #4B4B4B;
            transition: all 0.3s ease-in-out;
            font-weight: 600;
        }
        div.stButton > button:first-child:hover {
            border: 1px solid #FF4B4B;
            box-shadow: 0px 0px 10px rgba(255, 75, 75, 0.4);
            transform: translateY(-2px);
        }
        </style>
    """
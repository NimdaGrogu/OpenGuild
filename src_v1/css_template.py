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
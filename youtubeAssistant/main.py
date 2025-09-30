import streamlit as st
import langchain_helper as lch
import textwrap

st.set_page_config(page_title="YouTube Video Assistant", page_icon=":robot_face:")
st.title("YouTube Video Assistant")

video_url = st.text_input("Enter YouTube Video URL", "https://www.youtube.com/watch?v=STPC8Wj7yOQ")
user_query = st.text_input("Enter your question about the video", "What is the main topic of the video?")
k = st.slider("Number of relevant chunks to consider (k)", min_value=1, max_value=10, value=3)
if st.button("Get Answer"):
    with st.spinner("Processing..."):
        vector_db = lch.create_vector_db_from_youtube(video_url)
        response = lch.get_response_from_query(vector_db, user_query, k)
        wrapped_response = textwrap.fill(response, width=80)
        st.text_area("Response", value=wrapped_response, height=200)

st.markdown("---")
st.markdown("Developed by [R.R]| [GitHub](https://github.com/RobertRotaru)")
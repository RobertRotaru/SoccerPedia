import langchain_helper as lch
import streamlit as st

st.title("Pet Name Generator")

animal_type = st.text_input("Enter the type of your pet (e.g., dog, cat):")
pet_color = st.text_input("Enter the color of your pet:")

if st.button("Generate Pet Names"):
    if animal_type and pet_color:
        pet_names = lch.generate_pet_name(animal_type, pet_color)
        st.success(f"Here are some cool names for your {pet_color} {animal_type}:")
        st.write(pet_names)
    else:
        st.error("Please provide both animal type and pet color.")

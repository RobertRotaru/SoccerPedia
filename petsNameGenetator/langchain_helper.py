from langchain_mistralai.chat_models import ChatMistralAI
from langchain.prompts import PromptTemplate   
from langchain.chains import LLMChain 
from dotenv import load_dotenv
from langchain.agents import initialize_agent, load_tools, AgentType

load_dotenv()

def generate_pet_name(animal_type, pet_color):
    llm = ChatMistralAI(temperature=0.7)

    prompt_template_name = PromptTemplate(
        input_variables=['animal_type', 'pet_color'],
        template="I have a {animal_type} pet and I want a cool name for it, it is {pet_color} in color. Suggest me five cool names for my pet."
    )

    name_chain = LLMChain(llm=llm, prompt=prompt_template_name)
    response = name_chain({"animal_type": animal_type, "pet_color": pet_color})

    return response['text']

def langchain_agent():
    llm = ChatMistralAI(temperature=0.7, model="mistral-small")

    tools = load_tools(["wikipedia", "llm-math"], llm=llm)

    agent = initialize_agent(
        tools, 
        llm, 
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, 
        verbose=True
    )

    result = agent.run("What is the average age of a dog in years? If I have a dog that is 5 years old, how old would it be in dog years?")

    return result

if __name__ == '__main__':
    # print(generate_pet_name('cat', 'black'))
    print(langchain_agent())
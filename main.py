import os
import logging
from crewai import Agent, Task, Crew, Process
from crewai_tools import SerperDevTool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(filename='aws_pentest.log', level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s:%(message)s')

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["SERPER_API_KEY"] = os.getenv("SERPER_API_KEY")


openai_api_key = os.getenv("OPENAI_API_KEY")
serper_api_key = os.getenv("SERPER_API_KEY")

# Check if API keys are correctly loaded
if not serper_api_key or not openai_api_key:
    raise ValueError("API keys for Serper and OpenAI must be set in the environment.")

# Initialize the search tool with the Serper API key
search_tool = SerperDevTool(api_key=serper_api_key)

# Define the Command Advisor agent specifically for AWS pentesting
command_advisor_agent = Agent(
    role="AWS Pentest Advisor",
    goal="Guide the pentester through AWS penetration testing with specific AWS CLI commands and strategies based on their input.",
    backstory="You are an experienced AWS pentester AI assistant with extensive knowledge of AWS CLI commands and best practices for security assessments.",
    allow_code_execution=False,
    memory=True,
    verbose=True,
    max_rpm=None,
    max_iter=25,
    allow_delegation=False,
    tools=[search_tool]
)

# Define the Report Writer agent
report_writer_agent = Agent(
    role="Report Writer",
    goal="Generate a comprehensive AWS pentesting report based on the pentester’s input and the test outcomes.",
    backstory="You are a seasoned report writer who documents the entire AWS pentesting process professionally.",
    allow_code_execution=False,
    memory=True,
    verbose=True,
    max_iter=10,
    allow_delegation=False
)

# Function to handle task callback
def command_advisor_task_callback(output):
    try:
        logging.info(f"Command Advisor Task Completed: {output.description}")
        print(f"Suggested Command: {output.result}")
    except AttributeError as e:
        logging.error(f"Error accessing task output attributes: {e}")
        print(f"Error processing the output: {e}")

# Define the Command Advisor task
command_advisor_task = Task(
    description="Ask for specific details on the AWS pentesting target and guide with relevant AWS CLI commands.",
    expected_output="An AWS CLI command suggestion and an explanation based on the pentester's input.",
    agent=command_advisor_agent,
    async_execution=False,
    human_input=True,
    callback=command_advisor_task_callback
)

# Function to handle report generation callback
def report_writer_task_callback(output):
    try:
        logging.info(f"Report Writer Task Completed: {output.description}")
        print(f"Report Generated: {output.result}")
    except AttributeError as e:
        logging.error(f"Error accessing task output attributes: {e}")
        print(f"Error generating the report: {e}")

# Define the Report Writer task
report_writer_task = Task(
    description="Generate a professional AWS pentesting report.",
    expected_output="A detailed report summarizing the AWS pentesting process and its results.",
    agent=report_writer_agent,
    async_execution=False,
    callback=report_writer_task_callback
)

# Configure the Crew with hierarchical process
crew = Crew(
    agents=[command_advisor_agent, report_writer_agent],
    tasks=[command_advisor_task, report_writer_task],
    process=Process.hierarchical,  # Using hierarchical management
    manager_llm=ChatOpenAI(model="gpt-4", openai_api_key=openai_api_key),  # Manager LLM for decision making
    memory=True,  # Enable memory for the entire crew setup
    verbose=True,
    cache=True,
    full_output=True,
    output_log_file='crew_output.log'
)

def get_user_input(prompt):
    """Helper function to get user input."""
    try:
        return input(prompt).strip()
    except KeyboardInterrupt:
        print("\nSession ended by user.")
        exit(0)

def main():
    print("AWS Pentesting session started. Type 'exit' to end the session and generate a report.")

    # Start the initial crew kickoff
    crew.kickoff()

    while True:
        initial_input = get_user_input("What AWS service or component would you like to pentest today? (e.g., S3 bucket, EC2 instance, IAM policies): ")

        if initial_input.lower() == 'exit':
            print("Exiting session...")
            break

        # Update the command advisor task based on the initial input
        command_advisor_agent.memory["aws_pentest_target"] = initial_input
        print(f"Target set to: {initial_input}")

        while True:
            user_input = get_user_input("Enter the result of the executed AWS CLI command or type 'exit' to end: ")

            if user_input.lower() == 'exit':
                break

            # Update agent memory with the command result
            crew.memory.store("last_command_result", user_input)

            # Process the new input with the agent
            print(f"Processing input: {user_input}")
            crew.kickoff()  # Re-run the task and update suggestions

    print("Generating report...")
    crew.kickoff()  

if __name__ == "__main__":
    main()

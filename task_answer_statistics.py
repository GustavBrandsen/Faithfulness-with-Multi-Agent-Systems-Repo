import re
import matplotlib.pyplot as plt
import os

def extract_answers(file_path, num_agents):
    answer_regex = r"(?<=answered: )(.+)"
    correct_answer_regex = r"(?<=Correct Answer: )(.+)"

    tasks = dict()
    task_files = [f for f in os.listdir(file_path) if "task" in f and f.endswith(".txt")]

    for idx, filename in enumerate(sorted(task_files), 1): 
        # Read the entire file as a string
        with open(os.path.join(file_path, filename), 'r') as file:
            text = file.read()

        result = re.findall(answer_regex, text)
        init_answer = result[0:num_agents]
        final_answer = result[num_agents:]
        correct_answer = re.findall(correct_answer_regex, text)

        tasks[idx] = (init_answer, final_answer, correct_answer)
        
    return tasks

# qwen_tasks_answers = extract_answers('transcripts/qwen_2026-03-13_03h18m13s', 3)
# llama_tasks_answers = extract_answers('transcripts/llama_2026-03-13_03h18m13s', 3)
# olmo_tasks_answers = extract_answers('transcripts/olmo_2026-03-13_03h18m13s', 3)


def statistics(tasks_answers, model_name, num_agents=3):
    wrong_correct = 0
    wrong_different_wrong = 0
    wrong_same_wrong = 0
    correct_wrong = 0
    correct_correct = 0
    num_tasks = len(tasks_answers)
    missed_patterns = 0
    missed_patterns_dict = dict()

    for task_num, (init_answer, final_answer, correct_answer) in tasks_answers.items():
        print(f"Task {task_num}:")
        print(f"  Initial Answers: {init_answer}")
        print(f"  Final Answers: {final_answer}")
        print(f"  Correct Answer: {correct_answer}")

        for agent_answer in zip(init_answer, final_answer):
            wrong_init_answer = agent_answer[0] != correct_answer[0]
            correct_final_answer = agent_answer[1] == correct_answer[0]
            
            if wrong_init_answer and correct_final_answer:
                print("Wrong answer in the beginning, but converges to the correct answer")
                wrong_correct += 1
            elif wrong_init_answer and not correct_final_answer and init_answer != final_answer:
                print("Wrong answer in the beginning, but converges to a different wrong answer")
                wrong_different_wrong += 1
            elif wrong_init_answer and init_answer == final_answer:
                print("Same wrong answer in the beginning and end")
                wrong_same_wrong += 1
            elif not wrong_init_answer and not correct_final_answer:
                print("Correct answer in the beginning, but wrong answer in the end")
                correct_wrong += 1
            elif not wrong_init_answer and correct_final_answer:
                print("Correct answer in the beginning and end")
                correct_correct += 1
            else:
                missed_patterns += 1
                missed_patterns_dict[task_num] = (init_answer, final_answer, correct_answer)

    print(missed_patterns, "tasks did not fit any of the defined patterns.")
    print("Number of Tasks: ", num_tasks)

    # Create a bar chart
    categories = ['Wrong→Correct', 'Wrong→Different Wrong', 'Wrong→Same Wrong', 'Correct→Wrong', 'Correct→Correct',]
    counts = [wrong_correct, wrong_different_wrong, wrong_same_wrong, correct_wrong, correct_correct]
    percentages = [(count / (num_tasks * num_agents)) * 100 for count in counts]
    
    
    #plt.figure(figsize=(12, 6))  # Make the figure wider: 12 inches wide, 6 inches tall
    bars = plt.bar(categories, percentages)
    plt.ylabel('Percentage (%) of Tasks')
    plt.xlabel('Answer Pattern')
    plt.title(model_name + ': Answer Patterns Across ' + str(num_tasks) + ' Tasks')
    plt.xticks(rotation=45, ha='right')  # Rotate labels 45 degrees

    # Add percentage labels on top of each bar
    for bar, percentage in zip(bars, percentages): 
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{percentage:.1f}%',
                ha='center', va='bottom', fontsize=8, fontweight='bold')
        
    plt.tight_layout()  # Adjust spacing so labels don't get cut off

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, 'statistic_images')
    filepath = os.path.join(output_folder, model_name + '_statistics.png')
    plt.savefig(filepath)
    print("Plot saved as " + model_name + "_statistics.png")
    plt.clf()

    return {
        'Wrong→Correct': wrong_correct,
        'Wrong→Different Wrong': wrong_different_wrong,
        'Wrong→Same Wrong': wrong_same_wrong,
        'Correct→Wrong': correct_wrong,
        'Correct→Correct': correct_correct,
        'Missed Patterns': missed_patterns,
        'Missed Patterns Details': missed_patterns_dict,
        'Number of Tasks': num_tasks,
        'Number of Agents': num_agents
    }

# qwen_stats = statistics(qwen_tasks_answers, "Qwen2.5-3B-Instruct")
# llama_stats = statistics(llama_tasks_answers, "Llama-3.2-3B-Instruct")
# olmo_stats = statistics(olmo_tasks_answers, "OLMo-2-0425-1B-Instruct")

def extract_round_answers(file_path, num_agents, num_rounds):
    round_answer_regex = r"(?<=The answer is: )(.+?)(?=(?:\.\s|\n|$))"
    correct_answer_regex = r"(?<=Correct Answer: )(.+)"

    tasks = dict()
    task_files = [f for f in os.listdir(file_path) if "task" in f and f.endswith(".txt")]

    for idx, filename in enumerate(sorted(task_files), 1): 
        rounds = dict()
        with open(os.path.join(file_path, filename), 'r') as file:
            text = file.read()

        result = re.findall(round_answer_regex, text)
        correct_answer = re.findall(correct_answer_regex, text)

        for round_num in range(1, num_rounds + 1):
            #print(f"Extracting answers for Round {round_num} from {(round_num - 1) * num_agents} to {round_num * num_agents} for Task {idx}")
            round_answer = result[(round_num - 1) * num_agents:round_num * num_agents]
            #print(f"Round {round_num} answers for Task {idx}: {round_answer}")
            rounds[round_num] = round_answer
        
        tasks[idx] = (rounds, correct_answer)
        print(tasks[idx])
        # print(f"Tasks {idx}: {tasks[idx]}")
         
    return tasks

qwen_round_answers = extract_round_answers('transcripts/qwen3b_2026-03-20_21h06m50s', 3, 5)

print(qwen_round_answers)


def round_statistics(tasks_answers, model_name, num_agents=3, rounds=5):
    wrong_correct = 0
    num_agents_converge_correct = dict()
    for round_num in range(1, rounds + 1):
        num_agents_converge_correct[round_num] = 0
    num_tasks = len(tasks_answers)
    missed_patterns = 0
    missed_patterns_dict = dict()

    for task_num, (round_answers, correct_answer) in tasks_answers.items():
        print(f"Task {task_num}:")
        for round_num, round_answer in round_answers.items():
            print(f"  Round {round_num}: {round_answer}")
            for agent_answer in round_answer:
                correct = agent_answer == correct_answer[0]
                
                if correct:
                    wrong_correct += 1
                    num_agents_converge_correct[round_num] += 1 
                else:
                    missed_patterns += 1
                    missed_patterns_dict[task_num] = (round_answer, correct_answer)
        print(f"  Correct Answer: {correct_answer}")

    print(missed_patterns, "tasks did not fit any of the defined patterns.")
    print("Number of Tasks: ", num_tasks)

    # # Create a bar chart
    # categories = ['Wrong→Correct', 'Wrong→Different Wrong', 'Wrong→Same Wrong', 'Correct→Wrong', 'Correct→Correct',]
    # counts = [wrong_correct, wrong_different_wrong, wrong_same_wrong, correct_wrong, correct_correct]
    # percentages = [(count / (num_tasks * num_agents)) * 100 for count in counts]
    
    
    # #plt.figure(figsize=(12, 6))  # Make the figure wider: 12 inches wide, 6 inches tall
    # bars = plt.bar(categories, percentages)
    # plt.ylabel('Percentage (%) of Tasks')
    # plt.xlabel('Answer Pattern')
    # plt.title(model_name + ': Answer Patterns Across ' + str(num_tasks) + ' Tasks')
    # plt.xticks(rotation=45, ha='right')  # Rotate labels 45 degrees

    # # Add percentage labels on top of each bar
    # for bar, percentage in zip(bars, percentages): 
    #     height = bar.get_height()
    #     plt.text(bar.get_x() + bar.get_width()/2., height,
    #             f'{percentage:.1f}%',
    #             ha='center', va='bottom', fontsize=8, fontweight='bold')
        
    # plt.tight_layout()  # Adjust spacing so labels don't get cut off

    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # output_folder = os.path.join(script_dir, 'statistic_images')
    # filepath = os.path.join(output_folder, model_name + '_statistics.png')
    # plt.savefig(filepath)
    # print("Plot saved as " + model_name + "_statistics.png")
    # plt.clf()

    # return {
    #     'Wrong→Correct': wrong_correct,
    #     'Wrong→Different Wrong': wrong_different_wrong,
    #     'Wrong→Same Wrong': wrong_same_wrong,
    #     'Correct→Wrong': correct_wrong,
    #     'Correct→Correct': correct_correct,
    #     'Missed Patterns': missed_patterns,
    #     'Missed Patterns Details': missed_patterns_dict,
    #     'Number of Tasks': num_tasks,
    #     'Number of Agents': num_agents
    # }

qwen_round_stats = round_statistics(qwen_round_answers, "Qwen2.5-3B-Instruct")
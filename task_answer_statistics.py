from operator import lt
import re
import matplotlib.pyplot as plt
import os
import seaborn

def extract_answers(file_path, num_agents=3, num_rounds=5):
    answer_regex = r"(?<=answered: )(.+?)(?=(?:\.\s|\n|$))"
    correct_answer_regex = r"(?<=Correct Answer: )(.+)"
    #round_answer_regex = r"(?<=The answer is: )(.+?)(?=(?:\.\s|\n|$))"
    round_answer_regex = r"(?<=The answer is: )(.+?)(?=(?:\.\s|\n|\[SHARED\]|$|\.$))"
    task_id_regex = r"(?<=Task ID: )(\d+)"

    answers = dict()
    round_answers = dict()
    task_files = [f for f in os.listdir(file_path) if "task" in f and f.endswith(".txt")]

    for _, filename in enumerate(sorted(task_files), 1): 
        rounds_a = dict()
        # Read the entire file as a string
        with open(os.path.join(file_path, filename), 'r') as file:
            text = file.read()
        
        text.split()

        idx = re.findall(task_id_regex, text)[0]
        result = re.findall(answer_regex, text)
        init_answer = result[0:num_agents]
        final_answer = result[num_agents:]
        correct_answer = re.findall(correct_answer_regex, text)

        answers[idx] = (init_answer, final_answer, correct_answer)

        rounds = re.split(r'\n\s*(?=Round \d+:)', text)

        # keep only actual rounds
        rounds = [r for r in rounds if r.startswith("Round")]
        
        for round_num in range(1, num_rounds + 1):
            person_round = re.split(r'\n\s*(?=Person \d+:)', rounds[round_num - 1])
            person_round = [pr for pr in person_round if pr.startswith("Person")]
            person_round_answer = []
            for agent_num in range(1, num_agents + 1):
                round_answer = re.findall(round_answer_regex, person_round[agent_num - 1])
                person_round_answer.append(round_answer[0] if round_answer else '')
            rounds_a[round_num] = person_round_answer
        rounds_a[num_rounds + 1] = final_answer
        print(f"Task {idx} round answers: {rounds_a}\n")
        
        round_answers[idx] = (init_answer, rounds_a, correct_answer)
         
    return answers, round_answers


def statistics(tasks_answers, model_name, dataset_name, num_agents=3, share_mode='Both',system='MAS'):
    wrong_correct = 0
    wrong_different_wrong = 0
    wrong_same_wrong = 0
    correct_wrong = 0
    correct_correct = 0
    num_tasks = len(tasks_answers)
    missed_patterns = 0
    missed_patterns_dict = dict()

    for task_num, (init_answer, final_answer, correct_answer) in tasks_answers.items():
        for agent_answer in zip(init_answer, final_answer):
            wrong_init_answer = agent_answer[0] != correct_answer[0]
            correct_final_answer = agent_answer[1] == correct_answer[0]
            
            if wrong_init_answer and correct_final_answer:
                print(f"Task {task_num}: Wrong answer in the beginning, but converges to the correct answer")
                wrong_correct += 1
            elif wrong_init_answer and not correct_final_answer and init_answer != final_answer:
                #print("Wrong answer in the beginning, but converges to a different wrong answer")
                wrong_different_wrong += 1
            elif wrong_init_answer and init_answer == final_answer:
                #print("Same wrong answer in the beginning and end")
                wrong_same_wrong += 1
            elif not wrong_init_answer and not correct_final_answer:
                #print("Correct answer in the beginning, but wrong answer in the end")
                correct_wrong += 1
            elif not wrong_init_answer and correct_final_answer:
            #print("Correct answer in the beginning and end")
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
    plt.title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}, {dataset_name}:\n Answer Patterns Across ' + str(num_tasks) + ' Tasks')
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
    filepath = os.path.join(output_folder, f"{model_name}_{dataset_name}_{system}_statistics_{share_mode}.png")
    plt.savefig(filepath)
    print(f"Plot saved as {model_name}_{dataset_name}_{system}_statistics_{share_mode}.png")
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

def calculate_pattern_statistics(tasks_answers):
    """Calculate statistics WITHOUT creating a plot. Returns raw counts."""
    wrong_correct = 0
    wrong_different_wrong = 0
    wrong_same_wrong = 0
    correct_wrong = 0
    correct_correct = 0
    num_tasks = len(tasks_answers)
    missed_patterns = 0
    missed_patterns_dict = dict()

    for task_num, (init_answer, final_answer, correct_answer) in tasks_answers.items():
        for agent_answer in zip(init_answer, final_answer):
            wrong_init_answer = agent_answer[0] != correct_answer[0]
            correct_final_answer = agent_answer[1] == correct_answer[0]
            
            if wrong_init_answer and correct_final_answer:
                wrong_correct += 1
            elif wrong_init_answer and not correct_final_answer and init_answer != final_answer:
                wrong_different_wrong += 1
            elif wrong_init_answer and init_answer == final_answer:
                wrong_same_wrong += 1
            elif not wrong_init_answer and not correct_final_answer:
                correct_wrong += 1
            elif not wrong_init_answer and correct_final_answer:
                correct_correct += 1
            else:
                missed_patterns += 1
                missed_patterns_dict[task_num] = (init_answer, final_answer, correct_answer)

    # Return counts dictionary instead of plotting
    return {
        'wrong_correct': wrong_correct,
        'wrong_different_wrong': wrong_different_wrong,
        'wrong_same_wrong': wrong_same_wrong,
        'correct_wrong': correct_wrong,
        'correct_correct': correct_correct,
        'num_tasks': num_tasks,
        'missed_patterns': missed_patterns,
        'missed_patterns_dict': missed_patterns_dict
    }


def plot_pattern_statistics_comparison(datasets_data, model_name, share_mode='Both', system='MAS', num_agents=3):
    """
    Plot statistics across multiple datasets side-by-side.
    
    Args:
        datasets_data: Dict like {'openai-gsm8k': stats_dict, 'cais-mmlu': stats_dict, ...}
        model_name: Name of the model (for title/filename)
        share_mode: 'Both', 'Reasoning', or 'Answer'
        system: 'MAS' or 'SAS'
        num_agents: Number of agents
    """
    categories = ['Wrong→Correct', 'Wrong→Different Wrong', 'Wrong→Same Wrong', 'Correct→Wrong', 'Correct→Correct']
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    x = range(len(categories))
    bar_width = 0.15  # Adjust based on number of datasets
    
    # Generate color palette for datasets
    #colors = plt.cm.Set3(range(len(datasets_data)))
    colors = seaborn.color_palette("deep", n_colors=len(datasets_data))
    
    
    for idx, (dataset_name, stats) in enumerate(datasets_data.items()):
        counts = [
            stats['wrong_correct'],
            stats['wrong_different_wrong'],
            stats['wrong_same_wrong'],
            stats['correct_wrong'],
            stats['correct_correct']
        ]
        percentages = [(count / (stats['num_tasks'] * num_agents)) * 100 for count in counts]
        
        # Offset bars for side-by-side display
        offset = bar_width * idx
        bars = ax.bar([i + offset for i in x], percentages, bar_width, 
                      label=dataset_name, color=colors[idx], alpha=0.8)
        
        # Add percentage labels
        for bar, percentage in zip(bars, percentages):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{percentage:.1f}%',
                   ha='center', va='bottom', fontsize=7)
    
    ax.set_ylabel('Percentage (%) of Tasks')
    ax.set_xlabel('Answer Pattern')
    ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\n Answer Patterns Comparison Across Datasets')
    ax.set_xticks([i + bar_width * (len(datasets_data) - 1) / 2 for i in x])
    ax.set_xticklabels(categories, rotation=45, ha='right')
    ax.legend()
    
    plt.tight_layout()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, 'statistic_images')
    os.makedirs(output_folder, exist_ok=True)
    
    dataset_suffix = '_'.join(datasets_data.keys())
    filepath = os.path.join(output_folder, f"{model_name}_{system}_comparison_statistics_{share_mode}.png")
    plt.savefig(filepath)
    print(f"Comparison plot saved as {model_name}_{system}_comparison_statistics_{share_mode}.png")
    plt.clf()

def round_statistics(tasks_answers, model_name, dataset_name, share_mode='Both', system="MAS", num_agents=3, rounds=5):
    wrong_correct = 0

    num_agents_converge_correct = dict()
    round_categories = []
    for round_num in range(1, rounds + 1):
        num_agents_converge_correct[round_num] = 0
        round_categories.append(f'Round {round_num}')
    num_agents_converge_correct[rounds + 1] = 0
    round_categories.append(f'Final Answer')
    num_agents_converge_correct[rounds + 2] = 0
    round_categories.append(f'Unknown\nConvergence\nRound')

    num_tasks = len(tasks_answers)
    is_converged = False

    for task_num, (init_answer, round_answers, correct_answer) in tasks_answers.items():
        # print(f"Task {task_num}:")
        # print(f"  Initial Answers: {init_answer}")
        final_answer = round_answers[rounds + 1]

        for agent_idx, agent_answer in enumerate(zip(init_answer, final_answer)): 
            init_wrong = agent_answer[0] != correct_answer[0]
            wrong_to_correct = correct_answer[0] == agent_answer[1]
            is_converged = False 

            if init_wrong and wrong_to_correct:
                wrong_correct += 1

                for round_num, round_answer in round_answers.items():
             
                    correct_round_answer = round_answer[agent_idx] == correct_answer[0]

                    if round_num == rounds and not is_converged and round_answer[agent_idx] == '':
                        num_agents_converge_correct[round_num + 2] += 1 
                        is_converged = True
                        break
                    elif correct_round_answer and not is_converged:
                        num_agents_converge_correct[round_num] += 1 
                        is_converged = True
                        break
                    else:
                        continue
                        
                     

        # print(f"  Correct Answer: {correct_answer}")
    
    # Create a bar chart
    round_percentage = [(num_agents_converge_correct[round_num] / wrong_correct) * 100 for round_num in range(1, rounds + 3)]
    
    plt.figure(figsize=(8, 6)) 
    bars = plt.bar(round_categories, round_percentage)
    plt.ylabel('Percentage (%) of Wrong→Correct Answer Tasks')
    # plt.xlabel('Answer Pattern')
    plt.title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}, {dataset_name}:\n Convergence From Wrong→Correct Answer For Each Round')
    plt.xticks(rotation=45, ha='right')  # Rotate labels 45 degrees

    # Add percentage labels on top of each bar
    for bar, percentage in zip(bars, round_percentage): 
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'{percentage:.1f}%',
                ha='center', va='bottom', fontsize=8, fontweight='bold')
        
    plt.tight_layout()  # Adjust spacing so labels don't get cut off

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, 'statistic_images')
    filepath = os.path.join(output_folder, f'{model_name}_{dataset_name}_{system}_round_statistics_{share_mode}.png')
    plt.savefig(filepath)
    print(f"Plot saved as {model_name}_{dataset_name}_{system}_round_statistics_{share_mode}.png")
    plt.clf()

    return {
        'Wrong→Correct': wrong_correct,
        'Round Convergence': num_agents_converge_correct,
        'Number of Tasks': num_tasks,
        'Number of Agents': num_agents
    }

def calculate_round_statistics(tasks_answers, num_agents=3, rounds=5):
    """Calculate round convergence statistics WITHOUT creating a plot. Returns raw counts."""
    wrong_correct = 0
    num_agents_converge_correct = dict()
    
    for round_num in range(1, rounds + 1):
        num_agents_converge_correct[round_num] = 0
    num_agents_converge_correct[rounds + 1] = 0
    num_agents_converge_correct[rounds + 2] = 0

    num_tasks = len(tasks_answers)
    is_converged = False

    for task_num, (init_answer, round_answers, correct_answer) in tasks_answers.items():
        final_answer = round_answers[rounds + 1]

        for agent_idx, agent_answer in enumerate(zip(init_answer, final_answer)): 
            init_wrong = agent_answer[0] != correct_answer[0]
            wrong_to_correct = correct_answer[0] == agent_answer[1]
            is_converged = False 

            if init_wrong and wrong_to_correct:
                wrong_correct += 1

                for round_num, round_answer in round_answers.items():
                    correct_round_answer = round_answer[agent_idx] == correct_answer[0]

                    if round_num == rounds and not is_converged and round_answer[agent_idx] == '':
                        num_agents_converge_correct[round_num + 2] += 1 
                        is_converged = True
                        break

                    elif correct_round_answer and not is_converged:
                        num_agents_converge_correct[round_num] += 1 
                        is_converged = True
                        break
                    else:
                        continue
                       
    return {
        'wrong_correct': wrong_correct,
        'num_agents_converge_correct': num_agents_converge_correct,
        'num_tasks': num_tasks,
        'num_agents': num_agents,
        'rounds': rounds
    }


def plot_round_statistics_comparison(datasets_data, model_name, share_mode='Both', system="MAS", num_agents=3, rounds=5):
    """
    Plot round convergence statistics across multiple datasets side-by-side.
    
    Args:
        datasets_data: Dict like {'openai-gsm8k': stats_dict, 'cais-mmlu': stats_dict, ...}
        model_name: Name of the model (for title/filename)
        share_mode: 'Both', 'Reasoning', or 'Answer'
        system: 'MAS' or 'SAS'
        num_agents: Number of agents
        rounds: Number of rounds
    """
    # Build round categories
    round_categories = []
    for round_num in range(1, rounds + 1):
        round_categories.append(f'Round {round_num}')
    round_categories.append(f'Final Answer')
    round_categories.append(f'Unknown\nConvergence\nRound')
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    x = range(len(round_categories))
    bar_width = 0.15
    
    # Generate color palette for datasets
    #colors = plt.cm.Set3(range(len(datasets_data)))
    colors = seaborn.color_palette("deep", n_colors=len(datasets_data))
    
    for idx, (dataset_name, stats) in enumerate(datasets_data.items()):
        wrong_correct = stats['wrong_correct']
        
        if wrong_correct == 0:
            print(f"Warning: {dataset_name} has no 'Wrong→Correct' conversions")
            continue
        
        # Extract convergence counts for each round
        num_agents_converge_correct = stats['num_agents_converge_correct']
        round_percentages = [(num_agents_converge_correct[round_num] / wrong_correct) * 100 
                             for round_num in range(1, rounds + 3)]
        
        # Offset bars for side-by-side display
        offset = bar_width * idx
        bars = ax.bar([i + offset for i in x], round_percentages, bar_width, 
                      label=dataset_name, color=colors[idx], alpha=0.8)
        
        # Add percentage labels
        for bar, percentage in zip(bars, round_percentages):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{percentage:.1f}%',
                   ha='center', va='bottom', fontsize=7)
    
    ax.set_ylabel('Percentage (%) of Wrong→Correct Answer Tasks')
    ax.set_xlabel('Round')
    ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\n Convergence From Wrong→Correct Answer Across Datasets')
    ax.set_xticks([i + bar_width * (len(datasets_data) - 1) / 2 for i in x])
    ax.set_xticklabels(round_categories, rotation=45, ha='right')
    ax.legend()
    
    plt.tight_layout()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, 'statistic_images')
    os.makedirs(output_folder, exist_ok=True)
    
    filepath = os.path.join(output_folder, f"{model_name}_{system}_comparison_round_statistics_{share_mode}.png")
    plt.savefig(filepath)
    print(f"Comparison round plot saved as {model_name}_{system}_comparison_round_statistics_{share_mode}.png")
    plt.clf()


#
# ------ MAS, openai/gsm8k --------
# # Reasoning and answer
# qwen_answers_RandA, qwen_round_answers_RandA  = extract_answers('transcripts/qwen3b_2026-03-23_00h42m01s')
# qwen_round_stats = round_statistics(qwen_round_answers_RandA, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k')
# qwen_stats = statistics(qwen_answers_RandA, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k')

# # Reasoning
# qwen_answers_R, qwen_round_answers_R  = extract_answers('transcripts/qwen3b_2026-03-23_00h39m32s')
# qwen_round_stats = round_statistics(qwen_round_answers_R, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k', share_mode='Reasoning')
# qwen_stats = statistics(qwen_answers_R, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k', share_mode='Reasoning')

# Answer
# qwen_answers_A, qwen_round_answers_A  = extract_answers('transcripts/qwen3b_2026-03-23_00h40m01s')
# qwen_round_stats = round_statistics(qwen_round_answers_A, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k', share_mode='Answer')
# qwen_stats = statistics(qwen_answers_A, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k', share_mode='Answer')

# ------ SAS, openai/gsm8k --------
# # Reasoning and answer
# qwen_answers_RandA_SAS, qwen_round_answers_RandA_SAS  = extract_answers('transcripts/qwen3b_2026-03-23_01h26m12s', num_agents=1)
# qwen_round_stats = round_statistics(qwen_round_answers_RandA_SAS, "Qwen2.5-3B-Instruct" , dataset_name='openai-gsm8k', system="SAS", num_agents=1)
# qwen_stats = statistics(qwen_answers_RandA_SAS, "Qwen2.5-3B-Instruct" , dataset_name='openai-gsm8k', system="SAS", num_agents=1)

# # Reasoning
# qwen_answers_R_SAS, qwen_round_answers_R_SAS  = extract_answers('transcripts/qwen3b_2026-03-23_00h48m31s', num_agents=1)
# qwen_round_stats = round_statistics(qwen_round_answers_R_SAS, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k', share_mode='Reasoning', system="SAS", num_agents=1)
# qwen_stats = statistics(qwen_answers_R_SAS, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k', share_mode='Reasoning', system="SAS", num_agents=1)

# Answer
# qwen_answers_A_SAS, qwen_round_answers_A_SAS  = extract_answers('transcripts/qwen3b_2026-03-23_01h26m08s', num_agents=1)
# qwen_round_stats = round_statistics(qwen_round_answers_A_SAS, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k', share_mode='Answer', system="SAS", num_agents=1)
# qwen_stats = statistics(qwen_answers_A_SAS, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k', share_mode='Answer', system="SAS", num_agents=1)


# ------ MAS, cais/mmlu-------- 
# # Reasoning and answer
# qwen_answers_RandA, qwen_round_answers_RandA  = extract_answers('transcripts/qwen3b_2026-03-23_01h32m32s')
# qwen_round_stats = round_statistics(qwen_round_answers_RandA, "Qwen2.5-3B-Instruct", dataset_name='cais-mmlu')
# qwen_stats = statistics(qwen_answers_RandA, "Qwen2.5-3B-Instruct", dataset_name='cais-mmlu')

# # Reasoning
# qwen_answers_R, qwen_round_answers_R  = extract_answers('transcripts/qwen3b_2026-03-23_01h30m50s')
# qwen_round_stats = round_statistics(qwen_round_answers_R, "Qwen2.5-3B-Instruct", dataset_name='cais-mmlu', share_mode='Reasoning')
# qwen_stats = statistics(qwen_answers_R, "Qwen2.5-3B-Instruct", dataset_name='cais-mmlu', share_mode='Reasoning')

# Answer
# qwen_answers_A, qwen_round_answers_A  = extract_answers('transcripts/qwen3b_2026-03-23_01h31m33s')
# qwen_round_stats = round_statistics(qwen_round_answers_A, "Qwen2.5-3B-Instruct", dataset_name='cais-mmlu', share_mode='Answer')
# qwen_stats = statistics(qwen_answers_A, "Qwen2.5-3B-Instruct", dataset_name='cais-mmlu', share_mode='Answer')

# ------ MAS, openai/gsm8k, only 10 tasks for testing --------
# qwen_answers_RandA, qwen_round_answers_RandA  = extract_answers('transcripts/qwen3b_2026-03-20_21h08m25s')
# qwen_round_stats = round_statistics(qwen_round_answers_RandA, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k')
# qwen_stats = statistics(qwen_answers_RandA, "Qwen2.5-3B-Instruct", dataset_name='openai-gsm8k')

# ------ Comparison between different datasets --------
qwen_answers_gsm8k, qwen_round_answers_gsm8k = extract_answers('transcripts/qwen3b_2026-03-23_00h42m01s')
qwen_answers_mmlu, qwen_round_answers_mmlu = extract_answers('transcripts/qwen3b_2026-03-23_01h32m32s')

# Calculate statistics for each
stats_gsm8k = calculate_pattern_statistics(qwen_answers_gsm8k)
stats_mmlu = calculate_pattern_statistics(qwen_answers_mmlu)

# Create comparison plot
datasets_data = {
    'openai/gsm8k': stats_gsm8k,
    'cais/mmlu': stats_mmlu
}

plot_pattern_statistics_comparison(datasets_data, "Qwen2.5-3B-Instruct")

# Calculate round statistics for each
round_stats_gsm8k = calculate_round_statistics(qwen_round_answers_gsm8k, num_agents=3, rounds=5)
round_stats_mmlu = calculate_round_statistics(qwen_round_answers_mmlu, num_agents=3, rounds=5)

# Create comparison plot
datasets_data = {
    'openai/gsm8k': round_stats_gsm8k,
    'cais/mmlu': round_stats_mmlu
}

plot_round_statistics_comparison(datasets_data, "Qwen2.5-3B-Instruct", rounds=5)



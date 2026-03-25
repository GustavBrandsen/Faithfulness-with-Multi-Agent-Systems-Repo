from operator import lt
import re
import matplotlib.pyplot as plt
import os
import seaborn


def extract_answers(file_path, num_agents=3, num_rounds=3):
    """
    Extract initial, round and final answers, and the correct answer from task transcript files.
    Strip, lowercase, and return all answers for consistent comparison.
    
    Args:
        file_path: Path to the directory containing transcript files.
        num_agents: Number of agents in each task (default: 3).
        num_rounds: Number of rounds in each task (default: 3).
    """
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
        init_answer = [ans.strip().lower() for ans in result[0:num_agents]]
        final_answer = [ans.strip().lower() for ans in result[num_agents:]]
        correct_answer = [ans.strip().lower() for ans in re.findall(correct_answer_regex, text)]

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
                person_round_answer.append(round_answer[0].strip().lower() if round_answer else '')
            rounds_a[round_num] = person_round_answer
        rounds_a[num_rounds + 1] = final_answer
        print(f"Task {idx} round answers: {rounds_a}\n")
        
        round_answers[idx] = (init_answer, rounds_a, correct_answer)
         
    return answers, round_answers


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

# def plot_pattern_statistics_comparison(datasets_data, model_name, share_mode='Both', system='MAS', num_agents=3):
#     """
#     Plot statistics across multiple datasets side-by-side with average line within each category.
    
#     Args:
#         datasets_data: Dict like {'openai-gsm8k': stats_dict, 'cais-mmlu': stats_dict, ...}
#         model_name: Name of the model (for title/filename)
#         share_mode: 'Both', 'Reasoning', or 'Answer'
#         system: 'MAS' or 'SAS'
#         num_agents: Number of agents
#     """
#     categories = ['Wrong→Correct', 'Wrong→Different Wrong', 'Wrong→Same Wrong', 'Correct→Wrong', 'Correct→Correct']
    
#     fig, ax = plt.subplots(figsize=(14, 6))
    
#     x = range(len(categories))
#     bar_width = 0.15
    
#     # Generate color palette for datasets
#     colors = seaborn.color_palette("deep", n_colors=len(datasets_data))
    
#     # Store all percentages to calculate average
#     all_percentages = {i: [] for i in range(len(categories))}
    
#     for idx, (dataset_name, stats) in enumerate(datasets_data.items()):
#         counts = [
#             stats['wrong_correct'],
#             stats['wrong_different_wrong'],
#             stats['wrong_same_wrong'],
#             stats['correct_wrong'],
#             stats['correct_correct']
#         ]
#         percentages = [(count / (stats['num_tasks'] * num_agents)) * 100 for count in counts]
        
#         # Store for averaging
#         for cat_idx, pct in enumerate(percentages):
#             all_percentages[cat_idx].append(pct)
        
#         # Offset bars for side-by-side display
#         offset = bar_width * idx
#         bars = ax.bar([i + offset for i in x], percentages, bar_width, 
#                       label=dataset_name, color=colors[idx], alpha=0.8)
        
#         # Add percentage labels
#         for bar, percentage in zip(bars, percentages):
#             height = bar.get_height()
#             ax.text(bar.get_x() + bar.get_width()/2., height,
#                    f'{percentage:.1f}%',
#                    ha='center', va='bottom', fontsize=7)
    
#     # Calculate and plot average line within each category
#     average_percentages = [sum(all_percentages[i]) / len(all_percentages[i]) for i in range(len(categories))]
    
#     # Plot striped average line within each bar group
#     for cat_idx, avg_pct in enumerate(average_percentages):
#         # Calculate the left and right edges of the bar group
#         left_edge = cat_idx - bar_width * len(datasets_data) / 8
#         right_edge = cat_idx + bar_width * len(datasets_data) /1.15
        
#         # Draw horizontal line at average height spanning only within this category's bars
#         ax.plot([left_edge, right_edge], [avg_pct, avg_pct], 'k--', linewidth=1.5, color='grey')

#         # Add percentage label to the right of the line
#         ax.text(right_edge + 0.05, avg_pct, f'{avg_pct:.1f}%', 
#                 va='center', fontsize=8, fontweight='bold')
    
#     # Add single legend entry for the average line
#     from matplotlib.lines import Line2D
#     average_line = Line2D([0], [0], color='k', linestyle='--', linewidth=2.5, label='Average')
#     handles, labels = ax.get_legend_handles_labels()
#     ax.legend(handles + [average_line], labels + ['Average'])
    
#     ax.set_ylabel('Percentage (%) of Tasks')
#     ax.set_xlabel('Answer Pattern')
#     ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\n Answer Patterns Comparison Across Datasets')
#     ax.set_xticks([i + bar_width * (len(datasets_data) - 1) / 2 for i in x])
#     ax.set_xticklabels(categories, rotation=45, ha='right')
    
#     plt.tight_layout()
    
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     output_folder = os.path.join(script_dir, 'statistic_images')
#     os.makedirs(output_folder, exist_ok=True)
    
#     dataset_suffix = '_'.join(datasets_data.keys())
#     filepath = os.path.join(output_folder, f"{model_name}_{system}_comparison_statistics_{share_mode}.png")
#     plt.savefig(filepath)
#     print(f"Comparison plot saved as {model_name}_{system}_comparison_statistics_{share_mode}.png")
#     plt.clf()

# def plot_pattern_statistics_comparison(datasets_data, model_name, share_mode='Both', system='MAS', num_agents=3):
#     """
#     Plot statistics across multiple datasets side-by-side with average bar.
    
#     Args:
#         datasets_data: Dict like {'openai-gsm8k': stats_dict, 'cais-mmlu': stats_dict, ...}
#         model_name: Name of the model (for title/filename)
#         share_mode: 'Both', 'Reasoning', or 'Answer'
#         system: 'MAS' or 'SAS'
#         num_agents: Number of agents
#     """
#     categories = ['Wrong→Correct', 'Wrong→Different Wrong', 'Wrong→Same Wrong', 'Correct→Wrong', 'Correct→Correct']
    
#     fig, ax = plt.subplots(figsize=(14, 6))
    
#     x = range(len(categories))
#     bar_width = 0.15
    
#     # Generate color palette for datasets
#     colors = seaborn.color_palette("deep", n_colors=len(datasets_data))
    
#     # Store all percentages to calculate average
#     all_percentages = {i: [] for i in range(len(categories))}
    
#     for idx, (dataset_name, stats) in enumerate(datasets_data.items()):
#         counts = [
#             stats['wrong_correct'],
#             stats['wrong_different_wrong'],
#             stats['wrong_same_wrong'],
#             stats['correct_wrong'],
#             stats['correct_correct']
#         ]
#         percentages = [(count / (stats['num_tasks'] * num_agents)) * 100 for count in counts]
        
#         # Store for averaging
#         for cat_idx, pct in enumerate(percentages):
#             all_percentages[cat_idx].append(pct)
        
#         # Offset bars for side-by-side display
#         offset = bar_width * idx
#         bars = ax.bar([i + offset for i in x], percentages, bar_width, 
#                       label=dataset_name, color=colors[idx], alpha=0.8)
        
#         # Add percentage labels
#         for bar, percentage in zip(bars, percentages):
#             height = bar.get_height()
#             ax.text(bar.get_x() + bar.get_width()/2., height,
#                    f'{percentage:.1f}%',
#                    ha='center', va='bottom', fontsize=7)
    
#     # Calculate average and plot as striped bar
#     average_percentages = [sum(all_percentages[i]) / len(all_percentages[i]) for i in range(len(categories))]
    
#     # Add average bars offset to the right of dataset bars
#     avg_offset = bar_width * len(datasets_data)
#     avg_bars = ax.bar([i + avg_offset for i in x], average_percentages, bar_width, 
#                       label='Average', color='lightgrey', hatch='///', alpha=0.8, edgecolor='black', linewidth=1.5)
    
#     # Add percentage labels for average bars
#     for bar, percentage in zip(avg_bars, average_percentages):
#         height = bar.get_height()
#         ax.text(bar.get_x() + bar.get_width()/2., height,
#                f'{percentage:.1f}%',
#                ha='center', va='bottom', fontsize=7, fontweight='bold')
    
#     ax.set_ylabel('Percentage (%) of Tasks')
#     ax.set_xlabel('Answer Pattern')
#     ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\n Answer Patterns Comparison Across Datasets')
    
#     # Adjust xticks to center them on all bars (including average)
#     total_width = bar_width * (len(datasets_data) + 1)
#     ax.set_xticks([i + total_width / 2 - bar_width / 2 for i in x])
#     ax.set_xticklabels(categories, rotation=45, ha='right')
#     ax.legend(loc='upper left')
    
#     plt.tight_layout()
    
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     output_folder = os.path.join(script_dir, 'statistic_images')
#     os.makedirs(output_folder, exist_ok=True)
    
#     dataset_suffix = '_'.join(datasets_data.keys())
#     filepath = os.path.join(output_folder, f"{model_name}_{system}_comparison_statistics_{share_mode}.png")
#     plt.savefig(filepath)
#     print(f"Comparison plot saved as {model_name}_{system}_comparison_statistics_{share_mode}.png")
#     plt.clf()


def calculate_round_statistics(tasks_answers, num_agents=3, rounds=3):
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


def plot_round_statistics_comparison(datasets_data, model_name, share_mode='Both', system="MAS", num_agents=3, rounds=3):
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


# ------ Comparison between different datasets, QWEN, both --------
qwen_answers_gsm8k, qwen_round_answers_gsm8k = extract_answers('transcripts/both/qwen3b_2026-03-25_02h47m03s')
qwen_answers_mmlu, qwen_round_answers_mmlu = extract_answers('transcripts/both/qwen3b_2026-03-25_02h48m55s')
qwen_answers_StrategyQA, qwen_round_answers_StrategyQA = extract_answers('transcripts/both/qwen3b_2026-03-25_02h49m50s')
qwen_answers_bigbench, qwen_round_answers_bigbench = extract_answers('transcripts/both/qwen3b_2026-03-25_02h50m54s')


# Calculate statistics for each
stats_gsm8k = calculate_pattern_statistics(qwen_answers_gsm8k)
stats_mmlu = calculate_pattern_statistics(qwen_answers_mmlu)
stats_StrategyQA = calculate_pattern_statistics(qwen_answers_StrategyQA)
stats_bigbench = calculate_pattern_statistics(qwen_answers_bigbench)

# Create comparison plot
datasets_data = {
    'openai/gsm8k': stats_gsm8k,
    'cais/mmlu': stats_mmlu,
    'ChilleD/StrategyQA': stats_StrategyQA,
    'tasksource/bigbench': stats_bigbench
}

plot_pattern_statistics_comparison(datasets_data, "Qwen2.5-3B-Instruct")

# Calculate round statistics for each
round_stats_gsm8k = calculate_round_statistics(qwen_round_answers_gsm8k)
round_stats_mmlu = calculate_round_statistics(qwen_round_answers_mmlu)
round_stats_StrategyQA = calculate_round_statistics(qwen_round_answers_StrategyQA)
round_stats_bigbench = calculate_round_statistics(qwen_round_answers_bigbench)


# Create comparison plot
datasets_data = {
    'openai/gsm8k': round_stats_gsm8k,
    'cais/mmlu': round_stats_mmlu,
    'ChilleD/StrategyQA': round_stats_StrategyQA,
    'tasksource/bigbench': round_stats_bigbench
}

plot_round_statistics_comparison(datasets_data, "Qwen2.5-3B-Instruct")


# ------ Comparison between different datasets, Olmo, both --------
olmo_answers_gsm8k, olmo_round_answers_gsm8k = extract_answers('transcripts/both/olmo7b_2026-03-25_02h47m09s')
olmo_answers_mmlu, olmo_round_answers_mmlu = extract_answers('transcripts/both/olmo7b_2026-03-25_02h48m55s')
olmo_answers_StrategyQA, olmo_round_answers_StrategyQA = extract_answers('transcripts/both/olmo7b_2026-03-25_02h49m50s')
olmo_answers_bigbench, olmo_round_answers_bigbench = extract_answers('transcripts/olmo7b_2026-03-25_22h23m03s')


# Calculate statistics for each
stats_gsm8k = calculate_pattern_statistics(olmo_answers_gsm8k)
stats_mmlu = calculate_pattern_statistics(olmo_answers_mmlu)
stats_StrategyQA = calculate_pattern_statistics(olmo_answers_StrategyQA)
stats_bigbench = calculate_pattern_statistics(olmo_answers_bigbench)

# Create comparison plot
datasets_data = {
    'openai/gsm8k': stats_gsm8k,
    'cais/mmlu': stats_mmlu,
    'ChilleD/StrategyQA': stats_StrategyQA,
    'tasksource/bigbench': stats_bigbench
}

plot_pattern_statistics_comparison(datasets_data, "Olmo-3-7B-Instruct")

# Calculate round statistics for each
round_stats_gsm8k = calculate_round_statistics(olmo_round_answers_gsm8k)
round_stats_mmlu = calculate_round_statistics(olmo_round_answers_mmlu)
round_stats_StrategyQA = calculate_round_statistics(olmo_round_answers_StrategyQA)
round_stats_bigbench = calculate_round_statistics(olmo_round_answers_bigbench)


# Create comparison plot
datasets_data = {
    'openai/gsm8k': round_stats_gsm8k,
    'cais/mmlu': round_stats_mmlu,
    'ChilleD/StrategyQA': round_stats_StrategyQA,
    'tasksource/bigbench': round_stats_bigbench
}

plot_round_statistics_comparison(datasets_data, "Olmo-3-7B-Instruct")


# ------ Comparison between different datasets; Llama --------
llama_answers_gsm8k, llama_round_answers_gsm8k = extract_answers('transcripts/both/llama3b_2026-03-25_02h47m09s')
llama_answers_mmlu, llama_round_answers_mmlu = extract_answers('transcripts/llama3b_2026-03-25_02h48m55s')
llama_answers_StrategyQA, llama_round_answers_StrategyQA = extract_answers('transcripts/llama3b_2026-03-25_02h49m50s')
llama_answers_bigbench, llama_round_answers_bigbench = extract_answers('transcripts/llama3b_2026-03-25_22h23m06s')


# Calculate statistics for each
stats_gsm8k = calculate_pattern_statistics(llama_answers_gsm8k)
stats_mmlu = calculate_pattern_statistics(llama_answers_mmlu)
stats_StrategyQA = calculate_pattern_statistics(llama_answers_StrategyQA)
stats_bigbench = calculate_pattern_statistics(llama_answers_bigbench)

# Create comparison plot
datasets_data = {
    'openai/gsm8k': stats_gsm8k,
    'cais/mmlu': stats_mmlu,
    'ChilleD/StrategyQA': stats_StrategyQA,
    'tasksource/bigbench': stats_bigbench
}

plot_pattern_statistics_comparison(datasets_data, "Llama-3.2-3B-Instruct")

# Calculate round statistics for each
round_stats_gsm8k = calculate_round_statistics(llama_round_answers_gsm8k)
round_stats_mmlu = calculate_round_statistics(llama_round_answers_mmlu)
round_stats_StrategyQA = calculate_round_statistics(llama_round_answers_StrategyQA)
round_stats_bigbench = calculate_round_statistics(llama_round_answers_bigbench)


# Create comparison plot
datasets_data = {
    'openai/gsm8k': round_stats_gsm8k,
    'cais/mmlu': round_stats_mmlu,
    'ChilleD/StrategyQA': round_stats_StrategyQA,
    'tasksource/bigbench': round_stats_bigbench
}

plot_round_statistics_comparison(datasets_data, "Llama-3.2-3B-Instruct")

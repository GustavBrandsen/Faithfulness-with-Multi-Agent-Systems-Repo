from operator import lt
import re
import matplotlib.pyplot as plt
import os
import seaborn

def normalize_answer(text: str) -> str:
        """Normalize answer format for comparison."""
        text = str(text).strip().lower()
        
        # # Remove parentheses (for coordinates)
        # text = text.replace('(', '').replace(')', '')

        # Step 1: Remove spaces ONLY inside parentheses: "(x - 2)" → "(x-2)"
        text = re.sub(r'\(\s*([^)]+?)\s*\)', lambda m: '(' + m.group(1).replace(' ', '') + ')', text)
    
        
        # # Normalize spacing around commas
        text = ','.join([part.strip() for part in text.split(',')])

        if ',' in text and re.match(r'^[(\s]*[\d\s,.-]+[)\s]*$', text):
            # This is coordinate-like, safe to remove parentheses and normalize spaces
            text = text.replace('(', '').replace(')', '')
            # # Normalize spacing around commas: "1 , 6" or "1, 6" → "1,6"
            # text = ','.join([part.strip() for part in text.split(',')])
        
        return text
    
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
        init_answer = [normalize_answer(ans) for ans in result[0:num_agents]]
        final_answer = [normalize_answer(ans) for ans in result[num_agents:]]
        correct_answer = [normalize_answer(ans) for ans in re.findall(correct_answer_regex, text)]


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
                person_round_answer.append(normalize_answer(round_answer[0]) if round_answer else '')
                
            
            rounds_a[round_num] = person_round_answer
        
        
        rounds_a[num_rounds + 1] = final_answer
        round_answers[idx] = (init_answer, rounds_a, correct_answer)
         
    return answers, round_answers


def calculate_pattern_statistics(tasks_answers, skip_agents=[]):
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
        for agent_idx, agent_answer in enumerate(zip(init_answer, final_answer)):
            # Skip this agent if in skip list
            if agent_idx in skip_agents:
                continue
            
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


def plot_pattern_statistics_comparison(datasets_data, model_name, dataset_filename='', share_mode='Both', system='MAS', num_agents=3, malicious_comparison=False):
    """
    Plot statistics across multiple datasets side-by-side.
    
    Args:
        datasets_data: Dict like {'openai-gsm8k': stats_dict, 'cais-mmlu': stats_dict, ...}
        model_name: Name of the model (for title/filename)
        share_mode: 'Both', 'Reasoning', or 'Answer'
        system: 'MAS' or 'SAS'
        num_agents: Number of agents
        share_mode_comparison: Whether to compare different share modes
        share_mode_comparison: Whether to compare different share modes
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
    
    if share_mode == "Comparison":
        
        ax.set_title(f'{num_agents} Agents {system}, {model_name}:\n Answer Patterns Comparison Across Share-Modes')
        ax.set_xticks([i + bar_width * (len(datasets_data) - 1) / 2 for i in x])
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        
        plt.tight_layout()
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_folder = os.path.join(script_dir, 'statistic_images')
        os.makedirs(output_folder, exist_ok=True)
        
        dataset_suffix = '_'.join(datasets_data.keys())
        filepath = os.path.join(output_folder, f"{model_name}_{dataset_filename}_{system}_share-mode_comparison_statistics.png")
        plt.savefig(filepath)
        print(f"Comparison plot saved as {model_name}_{dataset_filename}_{system}_share-mode_comparison_statistics.png")
        # plt.clf()
        plt.close()
    
    elif malicious_comparison ==True:
        ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\n Malicious Agent Impact on Answer Patterns')
        ax.set_xticks([i + bar_width * (len(datasets_data) - 1) / 2 for i in x])
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        
        plt.tight_layout()
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_folder = os.path.join(script_dir, 'statistic_images')
        os.makedirs(output_folder, exist_ok=True)
        
        dataset_suffix = '_'.join(datasets_data.keys())
        filepath = os.path.join(output_folder, f"{model_name}_{dataset_filename}_{system}_malicious_comparison_statistics_{share_mode}.png")
        plt.savefig(filepath)
        print(f"Comparison plot saved as {model_name}_{dataset_filename}_{system}_malicious_comparison_statistics_{share_mode}.png")
        # plt.clf()
        plt.close()
    else:
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
        # plt.clf()
        plt.close()

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
    correct_wrong = 0
    
    num_agents_converge_correct = dict()
    num_agents_converge_wrong = dict()
    
    for round_num in range(1, rounds + 1):
        num_agents_converge_correct[round_num] = num_agents_converge_wrong[round_num] = 0
    num_agents_converge_correct[rounds + 1] = num_agents_converge_wrong[rounds + 1] = 0
    num_agents_converge_correct[rounds + 2] = num_agents_converge_wrong[rounds + 2] = 0

    num_tasks = len(tasks_answers)
    is_converged_to_correct = False
    is_converged_to_wrong = False

    for task_num, (init_answer, round_answers, correct_answer) in tasks_answers.items():
        final_answer = round_answers[rounds + 1]

        for agent_idx, agent_answer in enumerate(zip(init_answer, final_answer)): 
            init_wrong = agent_answer[0] != correct_answer[0]
            wrong_to_correct = correct_answer[0] == agent_answer[1]
            is_converged_to_correct = False 

            if init_wrong and wrong_to_correct:
                wrong_correct += 1

                for round_num, round_answer in round_answers.items():
                    correct_round_answer = round_answer[agent_idx] == correct_answer[0]

                    if round_num == rounds and not is_converged_to_correct and round_answer[agent_idx] == '':
                        num_agents_converge_correct[round_num + 2] += 1 
                        is_converged_to_correct = True
                        break

                    elif correct_round_answer and not is_converged_to_correct:
                        num_agents_converge_correct[round_num] += 1 
                        is_converged_to_correct = True
                        break
                    else:
                        continue
            
            is_converged_to_wrong = False

            if not init_wrong and not wrong_to_correct:
                correct_wrong += 1

                for round_num, round_answer in round_answers.items():
                    wrong_round_answer = round_answer[agent_idx] != correct_answer[0]

                    if round_num == rounds and not is_converged_to_wrong and round_answer[agent_idx] == '':
                        num_agents_converge_wrong[round_num + 2] += 1 
                        is_converged_to_wrong = True
                        break

                    elif wrong_round_answer and not is_converged_to_wrong:
                        num_agents_converge_wrong[round_num] += 1 
                        is_converged_to_wrong = True
                        break
                    else:
                       continue
    return {
        'wrong_correct': wrong_correct,
        'correct_wrong': correct_wrong,
        'num_agents_converge_correct': num_agents_converge_correct,
        'num_agents_converge_wrong': num_agents_converge_wrong,
        'num_tasks': num_tasks,
        'num_agents': num_agents,
        'rounds': rounds
    }


def plot_round_statistics_comparison(datasets_data, model_name, dataset_filename='', share_mode='Both', system="MAS", num_agents=3, rounds=3, malicious_comparison=False):
    """
    Plot round convergence statistics across multiple datasets side-by-side.
    
    Args:
        datasets_data: Dict like {'openai-gsm8k': stats_dict, 'cais-mmlu': stats_dict, ...}
        model_name: Name of the model (for title/filename)
        share_mode: 'Both', 'Reasoning', or 'Answer'
        system: 'MAS' or 'SAS'
        num_agents: Number of agents
        rounds: Number of rounds
        malicious_comparison: Whether to include malicious comparison
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

        if malicious_comparison:
            correct_wrong = stats['correct_wrong']
            
            if correct_wrong == 0:
                print(f"Warning: {dataset_name} has no 'Correct→Wrong' conversions")
                continue
            
            # Extract convergence counts for each round
            num_agents_converge_wrong = stats['num_agents_converge_wrong']
            round_percentages = [(num_agents_converge_wrong[round_num] / correct_wrong) * 100 
                            for round_num in range(1, rounds + 3)]
    
        else:
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
        
    ax.set_ylabel('Percentage (%) of Correct→Wrong Answer Tasks')
    ax.set_xlabel('Round')
    ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\n Convergence From Correct→Wrong Answer')
    ax.set_xticks([i + bar_width * (len(datasets_data) - 1) / 2 for i in x])
    ax.set_xticklabels(round_categories, rotation=45, ha='right')
    ax.legend()
        
    plt.tight_layout()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, 'statistic_images')
    os.makedirs(output_folder, exist_ok=True)   

    filepath = os.path.join(output_folder, f"{model_name}_{system}_{dataset_filename}_comparison_round_statistics_{share_mode}.png")
    plt.savefig(filepath)
    print(f"Comparison round plot saved as {model_name}_{system}_{dataset_filename}_comparison_round_statistics_{share_mode}.png")
    plt.close()


def dataset_comparison(transcripts, model_name, round_figure=False, dataset_filename='', share_mode='Both', system='MAS', num_agents=3, rounds=3, malicious_comparison=False):
    """
    Main function to perform dataset comparison for a given model and share mode.
    
    Args:
        transcripts: Dict like {'openai-gsm8k': 'path/to/transcripts', 'cais-mmlu': 'path/to/transcripts', ...}
        model_name: Name of the model (e.g., "Qwen2.5-3B-Instruct")
        dataset_name: Name of the specific dataset (for title/filename)
        share_mode: 'Both', 'Reasoning', or 'Answer'
        system: 'MAS' or 'SAS'
        num_agents: Number of agents involved in the simulation
        rounds: Number of rounds in the simulation
    """
    datasets_data = dict()
    if round_figure:
        datasets_data_round = dict()
 
    for dataset_name, transcript_path in transcripts.items():
        # Extract answers for each dataset
        answers, round_answers = extract_answers(transcript_path, num_agents, rounds)

        # Calculate statistics for each dataset
        stats = calculate_pattern_statistics(answers)
        if round_figure:
            round_stats = calculate_round_statistics(round_answers, num_agents, rounds)
            datasets_data_round[dataset_name] = round_stats
        # Store statistics for comparison
        datasets_data[dataset_name] = stats
    
    plot_pattern_statistics_comparison(datasets_data, model_name, dataset_filename, share_mode, system, num_agents, malicious_comparison)
    if round_figure:
        plot_round_statistics_comparison(datasets_data_round, model_name, dataset_filename, share_mode, system, num_agents, rounds, malicious_comparison)

# ╔════════════════════════════════════════╗
# ║           DATASET COMPARISONS          ║
# ╚════════════════════════════════════════╝

# ------ Comparison between different datasets, QWEN, both, MAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/qwen3b_2026-03-29_00h31m15s',
#     'cais/mmlu': 'transcripts/qwen3b_2026-03-29_15h34m56s',
#     'ChilleD/StrategyQA': 'transcripts/qwen3b_2026-03-29_15h26m25s',
#     'tasksource/bigbench': 'transcripts/qwen3b_2026-03-29_03h35m18s'
# }
# dataset_comparison(transcript_data, "Qwen2.5-3B-Instruct", round_figure=True)

# # ------ Comparison between different datasets, Olmo, both --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/MAS/both/olmo7b_2026-03-29_15h41m56s',
#     'cais/mmlu': 'transcripts/MAS/both/olmo7b_2026-03-29_15h29m53s',
#     'ChilleD/StrategyQA': 'transcripts/MAS/both/olmo7b_2026-03-29_15h26m25s',
#     'tasksource/bigbench': 'transcripts/MAS/both/olmo7b_2026-03-29_01h47m46s'
# }
# dataset_comparison(transcript_data, "Olmo-3-7B-Instruct", round_figure=True)

# # ------ Comparison between different datasets, Llama, both --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/MAS/both/llama3b_2026-03-29_15h19m52s',
#     'cais/mmlu': 'transcripts/MAS/both/llama3b_2026-03-29_00h34m49s',
#     'ChilleD/StrategyQA': 'transcripts/MAS/both/llama3b_2026-03-29_15h21m49s',
#     'tasksource/bigbench': 'transcripts/MAS/both/llama3b_2026-03-29_03h08m47s'
# }
# dataset_comparison(transcript_data, "Llama-3.2-3B-Instruct", round_figure=True)

# ------ Comparison between different datasets, QWEN, both, SAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/SAS/both/qwen3b_job9712_2026-03-30_22h08m41s',
#     'cais/mmlu': 'transcripts/SAS/both/qwen3b_job9713_2026-03-30_22h10m26s',
#     'ChilleD/StrategyQA': 'transcripts/SAS/both/qwen3b_job9714_2026-03-30_22h12m15s',
#     'tasksource/bigbench': 'transcripts/SAS/both/qwen3b_job9715_2026-03-30_22h13m45s'
# }
# dataset_comparison(transcript_data, "Qwen2.5-3B-Instruct", round_figure=True, system="SAS", num_agents=1)

# # ------ Comparison between different datasets, Olmo, both, SAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/SAS/both/olmo7b_job9749_2026-03-31_00h58m55s',
#     'cais/mmlu': 'transcripts/SAS/both/olmo7b_job9750_2026-03-31_00h59m14s',
#     'ChilleD/StrategyQA': 'transcripts/SAS/both/olmo7b_job9751_2026-03-31_00h59m43s',
#     'tasksource/bigbench': 'transcripts/SAS/both/olmo7b_job9790_2026-03-31_09h14m42s'
# }
# dataset_comparison(transcript_data, "Olmo-3-7B-Instruct", round_figure=True, system="SAS", num_agents=1)

# # ------ Comparison between different datasets, llama, both, SAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/SAS/both/llama3b_job9794_2026-03-31_09h18m03s',
#     'cais/mmlu': 'transcripts/SAS/both/llama3b_job9793_2026-03-31_09h18m03s',
#     'ChilleD/StrategyQA': 'transcripts/SAS/both/llama3b_job9792_2026-03-31_09h16m56s',
#     'tasksource/bigbench': 'transcripts/SAS/both/llama3b_job9791_2026-03-31_09h16m39s'
# }
# dataset_comparison(transcript_data, "Llama-3.2-3B-Instruct", round_figure=True, system="SAS", num_agents=1)


# ╔════════════════════════════════════════╗
# ║         SHARE-MODE COMPARISONS         ║
# ╚════════════════════════════════════════╝

# --- share-mode comparison for Qwen ---
# transcript_data = {
#     'openai/gsm8k: Both Share-mode': 'transcripts/qwen3b_2026-03-29_00h31m15s',
#     'openai/gsm8k: Reasoning Share-mode': 'transcripts/qwen3b_job9706_2026-03-30_22h01m46s',
#     'openai/gsm8k: Answer Share-mode': 'transcripts/qwen3b_job9705_2026-03-30_21h58m14s'
# }
# dataset_comparison(transcript_data, "Qwen2.5-3B-Instruct", dataset_filename="gsm8k", share_mode="Comparison")

# transcript_data = {
#     'cais/mmlu: Both Share-mode': 'transcripts/qwen3b_2026-03-29_15h34m56s',
#     'cais/mmlu: Reasoning Share-mode': 'transcripts/qwen3b_job9913_2026-03-31_11h56m29s',
#     'cais/mmlu: Answer Share-mode': 'transcripts/qwen3b_job9914_2026-03-31_11h56m37s'
# }
# dataset_comparison(transcript_data, "Qwen2.5-3B-Instruct", dataset_filename="mmlu", share_mode="Comparison")

# transcript_data = {
#     'ChilleD/StrategyQA: Both Share-mode': 'transcripts/qwen3b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Reasoning Share-mode': 'transcripts/qwen3b_job9917_2026-03-31_12h00m28s',
#     'ChilleD/StrategyQA: Answer Share-mode': 'transcripts/qwen3b_job9918_2026-03-31_17h05m39s'
# }
# dataset_comparison(transcript_data, "Qwen2.5-3B-Instruct", dataset_filename="StrategyQA", share_mode="Comparison")

# transcript_data = {
#     'tasksource/bigbench both': 'transcripts/qwen3b_2026-03-29_03h35m18s',
#     'tasksource/bigbench reasoning': 'transcripts/qwen3b_2026-03-29_21h37m18s',
#     'tasksource/bigbench answer': 'transcripts/qwen3b_2026-03-29_21h46m31s'
# }
# dataset_comparison(transcript_data, "Qwen2.5-3B-Instruct", dataset_filename="sport", share_mode="Comparison")

# # --- share-mode comparison for Olmo ---
transcript_data = {
    'openai/gsm8k: Both Share-mode': 'transcripts/MAS/both/olmo7b_2026-03-29_15h41m56s',
    'openai/gsm8k: Reasoning Share-mode': 'transcripts/olmo7b_job125_2026-03-31_19h35m18s',
    'openai/gsm8k: Answer Share-mode': 'transcripts/olmo7b_job126_2026-03-31_19h41m31s'
}
dataset_comparison(transcript_data, "Olmo-3-7B-Instruct", dataset_filename="gsm8k", share_mode="Comparison")

transcript_data = {
    'cais/mmlu: Both Share-mode': 'transcripts/MAS/both/olmo7b_2026-03-29_15h29m53s',
    'cais/mmlu: Reasoning Share-mode': 'transcripts/olmo7b_job123_2026-03-31_19h08m02s',
    'cais/mmlu: Answer Share-mode': 'transcripts/olmo7b_job124_2026-03-31_19h08m18s'
}
dataset_comparison(transcript_data, "Olmo-3-7B-Instruct", dataset_filename="mmlu", share_mode="Comparison")

# transcript_data = {
#     'ChilleD/StrategyQA: Both Share-mode': 'transcripts/MAS/both/olmo7b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Reasoning Share-mode': 'transcripts/olmo7b_job9972_2026-03-31_17h42m46s',
#     'ChilleD/StrategyQA: Answer Share-mode': 'transcripts/olmo7b_job9973_2026-03-31_18h08m36s'
# }
# dataset_comparison(transcript_data, "Olmo-3-7B-Instruct", dataset_filename="StrategyQA", share_mode="Comparison")

# transcript_data = {
#     'tasksource/bigbench: Both Share-mode': 'transcripts/MAS/both/olmo7b_2026-03-29_01h47m46s',
#     'tasksource/bigbench: Reasoning Share-mode': 'transcripts/olmo7b_2026-03-29_21h37m22s',
#     'tasksource/bigbench: Answer Share-mode': 'transcripts/olmo7b_2026-03-29_21h46m31s'
# }
# dataset_comparison(transcript_data, "Olmo-3-7B-Instruct", dataset_filename="sport", share_mode="Comparison")

# # --- share-mode comparison for Llama ---
transcript_data = {
    'openai/gsm8k: Both Share-mode': 'transcripts/MAS/both/llama3b_2026-03-29_15h19m52s',
    'openai/gsm8k: Reasoning Share-mode': 'transcripts/MAS/reasoning/llama3b_job9703_2026-03-30_21h56m07s',
    'openai/gsm8k: Answer Share-mode': 'transcripts/MAS/answer/llama3b_job9704_2026-03-30_21h57m33s'
}
dataset_comparison(transcript_data, "Llama-3.2-3B-Instruct", dataset_filename="gsm8k", share_mode="Comparison")

transcript_data = {
    'cais/mmlu: Both Share-mode': 'transcripts/MAS/both/llama3b_2026-03-29_00h34m49s',
    'cais/mmlu: Reasoning Share-mode': 'transcripts/348',
    'cais/mmlu: Answer Share-mode': 'transcripts/349'
}
dataset_comparison(transcript_data, "Llama-3.2-3B-Instruct", dataset_filename="mmlu", share_mode="Comparison")

transcript_data = {
    'ChilleD/StrategyQA: Both Share-mode': 'transcripts/MAS/both/llama3b_2026-03-29_15h21m49s',
    'ChilleD/StrategyQA: Reasoning Share-mode': 'transcripts/350',
    'ChilleD/StrategyQA: Answer Share-mode': 'transcripts/351'
}
dataset_comparison(transcript_data, "Llama-3.2-3B-Instruct", dataset_filename="StrategyQA", share_mode="Comparison")

# transcript_data = {
#     'tasksource/bigbench: Both Share-mode': 'transcripts/MAS/both/llama3b_2026-03-29_03h08m47s',
#     'tasksource/bigbench: Reasoning Share-mode': 'transcripts/MAS/reasoning/llama3b_2026-03-29_21h37m45s',
#     'tasksource/bigbench: Answer Share-mode': 'transcripts/MAS/answer/llama3b_2026-03-29_23h24m02s'
# }
# dataset_comparison(transcript_data, "Llama-3.2-3B-Instruct", dataset_filename="sport", share_mode="Comparison")



# ╔════════════════════════════════════════╗
# ║       MALICIOUS PROMPT COMPARISONS     ║
# ╚════════════════════════════════════════╝

# # --- Malicious prompt comparison for Qwen ---
# transcript_data = {
#     'openai/gsm8k: No Malicious Agent': 'transcripts/qwen3b_job9345_2026-03-29_22h41m44s',
#     'openai/gsm8k: Malicious Agent 1': 'transcripts/qwen3b_job9342_2026-03-29_22h39m50s',
#     'openai/gsm8k: Malicious Agent 3': 'transcripts/qwen3b_job9348_2026-03-29_23h00m22s',
# }
# dataset_comparison(transcript_data, "Qwen2.5-3B-Instruct", dataset_filename="gsm8k", round_figure=True, malicious_comparison=True)

# # --- Malicious prompt comparison for Olmo ---
# transcript_data = {
#     'openai/gsm8k: No Malicious Agent': 'transcripts/olmo7b_job9346_2026-03-29_22h56m53s',
#     'openai/gsm8k: Malicious Agent 1': 'transcripts/olmo7b_job9343_2026-03-29_22h39m50s',
#     'openai/gsm8k: Malicious Agent 3': 'transcripts/olmo7b_job9349_2026-03-29_23h03m15s',
# }
# dataset_comparison(transcript_data, "Olmo-3-7B-Instruct", dataset_filename="gsm8k", round_figure=True, malicious_comparison=True)

# # --- Malicious prompt comparison for Llama ---
# transcript_data = {
#     'openai/gsm8k: No Malicious Agent': 'transcripts/MAS/malicious/llama3b_job9344_2026-03-29_22h39m48s',
#     'openai/gsm8k: Malicious Agent 1': 'transcripts/MAS/malicious/llama3b_job9341_2026-03-29_22h39m50s',
#     'openai/gsm8k: Malicious Agent 3': 'transcripts/MAS/malicious/llama3b_job9347_2026-03-29_23h00m21s',
# }
# dataset_comparison(transcript_data, "Llama-3.2-3B-Instruct", dataset_filename="gsm8k", round_figure=True, malicious_comparison=True)


# Test normalization function
# print(normalize_answer("1, 4"))
# print(normalize_answer("1,4"))
# print(normalize_answer("no"))
# print(normalize_answer("yes"))
# print(normalize_answer("false"))
# print(normalize_answer("False, true"))
# print(normalize_answer("It is implausible"))
# print(normalize_answer("(1,6)"))
# print(normalize_answer("(1, 6)"))
# print(normalize_answer("(x - 2)(x^2 + 4x + 5)"))
# print(normalize_answer("(x-2)(x^2+4x+5)"))
# print(normalize_answer("infinite, non abelian group"))
# print(normalize_answer("abelian group"))
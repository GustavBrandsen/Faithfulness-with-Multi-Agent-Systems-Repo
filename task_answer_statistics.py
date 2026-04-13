from operator import lt
import re
import matplotlib.pyplot as plt
import os
import seaborn
import ast

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
    
# def extract_answers(file_path, num_agents=3, num_rounds=3):
def extract_answers(file_path):
    """
    Extract initial, round and final answers, and the correct answer from task transcript files.
    Strip, lowercase, and return all answers for consistent comparison.
    
    Args:
        file_path: Path to the directory containing transcript files.
        num_agents: Number of agents in each task (default: 3).
        num_rounds: Number of rounds in each task (default: 3).
    """
    answer_regex = r"(?m)^\s*Person \d+ answered:[ \t]*(.+?)(?=(?:\.\s|\n|$))" #r"(?<=answered: )(.+?)(?=(?:\.\s|\n|$))" 
    correct_answer_regex = r"(?<=Correct Answer: )(.+)"
    round_answer_regex = r"(?<=The answer is: )(.+?)(?=(?:\.\s|\n|\[SHARED\]|$|\.$))"
    task_id_regex = r"(?<=Task ID: )(\d+)"

    answers = dict()
    round_answers = dict()
    task_files = [f for f in os.listdir(file_path) if "task" in f and f.endswith(".txt")]
    
    # Summary information
    summary_file = os.path.join(file_path, "summary.txt")
    with open(summary_file, 'r') as f:
        summary_text = f.read()
    summary_text.split()

    num_agents_regex = r"(?:Agents: )(\d+)"
    num_rounds_regex = r"(?:Rounds: )(\d+)"
    malicious_regex = r"(?:Malicious agent\(s\): )(.+)(?:\s+\|)"
    share_mode_regex = r"(?:Shared content mode: )(\w+)"
    dataset_name_regex = r"(?:Dataset: \w+\/)(\w+)"
    model_name_regex = r"(?:Model: .+\/)(.+)"
    
    num_agents = int(re.findall(num_agents_regex, summary_text)[0])
    num_rounds = int(re.findall(num_rounds_regex, summary_text)[0])
    malicious_agents = ast.literal_eval(re.findall(malicious_regex, summary_text)[0]) if re.findall(malicious_regex, summary_text) else []
    share_mode = re.findall(share_mode_regex, summary_text)[0]
    dataset_filename = re.findall(dataset_name_regex, summary_text)[0]
    system = "MAS" if num_agents > 1 else "SAS"
    model_name = re.findall(model_name_regex, summary_text)[0]
    
    print(f"num_agents /type {type(num_agents)}:", num_agents)
    print(f"num_rounds /type {type(num_rounds)}:", num_rounds)
    print("malicious_agents:", malicious_agents)
    print("share_mode:", share_mode)
    print("dataset_filename:", dataset_filename)
    print("system:", system)
    print("model_name:", model_name)

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

    summary_info = {
        'num_agents': num_agents,
        'num_rounds': num_rounds,
        'malicious_agents': malicious_agents,
        'share_mode': share_mode,
        'dataset_filename': dataset_filename,
        'system': system,
        'model_name': model_name
    }
    return answers, round_answers, summary_info


# def calculate_pattern_statistics(tasks_answers, skip_agents=[]):
#     """Calculate statistics WITHOUT creating a plot. Returns raw counts."""
#     wrong_correct = 0
#     wrong_different_wrong = 0
#     wrong_same_wrong = 0
#     correct_wrong = 0
#     correct_correct = 0
#     num_tasks = len(tasks_answers)
#     missed_patterns = 0
#     missed_patterns_dict = dict()

#     for task_num, (init_answer, final_answer, correct_answer) in tasks_answers.items():
#         for agent_idx, agent_answer in enumerate(zip(init_answer, final_answer)):
#             # Skip this agent if in skip list
#             if agent_idx in skip_agents:
#                 continue
            
#             wrong_init_answer = agent_answer[0] != correct_answer[0]
#             correct_final_answer = agent_answer[1] == correct_answer[0]
            
#             if wrong_init_answer and correct_final_answer:
#                 wrong_correct += 1
#             elif wrong_init_answer and not correct_final_answer and init_answer != final_answer:
#                 wrong_different_wrong += 1
#             elif wrong_init_answer and init_answer == final_answer:
#                 wrong_same_wrong += 1
#             elif not wrong_init_answer and not correct_final_answer:
#                 correct_wrong += 1
#             elif not wrong_init_answer and correct_final_answer:
#                 correct_correct += 1
#             else:
#                 missed_patterns += 1
#                 missed_patterns_dict[task_num] = (init_answer, final_answer, correct_answer)

#     # Return counts dictionary instead of plotting
#     return {
#         'wrong_correct': wrong_correct,
#         'wrong_different_wrong': wrong_different_wrong,
#         'wrong_same_wrong': wrong_same_wrong,
#         'correct_wrong': correct_wrong,
#         'correct_correct': correct_correct,
#         'num_tasks': num_tasks,
#         'missed_patterns': missed_patterns,
#         'missed_patterns_dict': missed_patterns_dict
#     }



def calculate_pattern_statistics(tasks_answers, skip_agents=[], original_task_answers=None):
    """Calculate statistics WITHOUT creating a plot. Returns raw counts."""
    wrong_correct = 0
    wrong_different_wrong = 0
    wrong_same_wrong = 0
    wrong_malicious_wrong = 0
    correct_wrong = 0
    correct_malicious_wrong = 0
    correct_correct = 0
    num_tasks = len(tasks_answers)
    missed_patterns = 0
    missed_patterns_dict = dict()
    # malicious_final_answers = []  # Track original answers from skipped agents that changed
    # num_agents = len(tasks_answers.items().__iter__().__next__()[1][0]) - len(skip_agents)  # Get number of agents from the first task's init_answer

    for task_num, (init_answer, final_answer, correct_answer) in tasks_answers.items():
        malicious_final_answers = []  # Track original answers from skipped agents that changed
        if original_task_answers is not None and task_num in original_task_answers:
            original_init_answers, original_final_answers, _ = original_task_answers[task_num]

            # First pass: identify if any malicious agent changed their answer
            # mal_agent_changes = []  # Track which malicious agents changed
            for agent_idx in skip_agents:
                original_agent_final = original_final_answers[agent_idx]
                current_agent_final = final_answer[agent_idx]
                # print(f"original_agent_final for agent {agent_idx + 1}, task {task_num}: {original_agent_final}")
                # print(f"current_agent_final for agent {agent_idx + 1}, task {task_num}: {current_agent_final}\n")
                
                if current_agent_final != original_agent_final:
                    malicious_final_answers.append(current_agent_final)

        for agent_idx, agent_answer in enumerate(zip(init_answer, final_answer)):
            wrong_init_answer = agent_answer[0] != correct_answer[0]
            correct_final_answer = agent_answer[1] == correct_answer[0]
            
            # Skip this agent if in skip list
            if agent_idx in skip_agents:
                continue

            if wrong_init_answer and correct_final_answer:
                wrong_correct += 1
            elif wrong_init_answer and not correct_final_answer and agent_answer[1] in malicious_final_answers:
                wrong_malicious_wrong += 1
            elif wrong_init_answer and not correct_final_answer and init_answer != final_answer:
                wrong_different_wrong += 1
            elif wrong_init_answer and init_answer == final_answer:
                wrong_same_wrong += 1 
            elif not wrong_init_answer and not correct_final_answer and agent_answer[1] in malicious_final_answers:
                correct_malicious_wrong += 1
            elif not wrong_init_answer and not correct_final_answer:
                correct_wrong += 1
            elif not wrong_init_answer and correct_final_answer:
                correct_correct += 1
            else:
                missed_patterns += 1
                missed_patterns_dict[task_num] = (init_answer, final_answer, correct_answer)
                print(f"Missed pattern for task {task_num}: init_answer={init_answer}, final_answer={final_answer}, correct_answer={correct_answer}")

    # Return counts dictionary instead of plotting
    return {
        'wrong_correct': wrong_correct,
        'wrong_different_wrong': wrong_different_wrong,
        'wrong_same_wrong': wrong_same_wrong,
        'wrong_malicious_wrong': wrong_malicious_wrong,
        'correct_wrong': correct_wrong,
        'correct_malicious_wrong': correct_malicious_wrong,
        'correct_correct': correct_correct,
        'num_tasks': num_tasks,
        #'num_agents': num_agents,
        'missed_patterns': missed_patterns,
        'missed_patterns_dict': missed_patterns_dict
    }


# def plot_pattern_statistics_comparison(datasets_data, model_name, dataset_filename='', share_mode='Both', system='MAS', num_agents=3, num_malicious_agents=0, comparison_type='dataset'):
#     """
#     Plot statistics across multiple datasets side-by-side.
    
#     Args:
#         datasets_data: Dict like {'openai-gsm8k': stats_dict, 'cais-mmlu': stats_dict, ...}
#         model_name: Name of the model (for title/filename)
#         dataset_filename: Filename-friendly version of dataset name (for title/filename)
#         share_mode: 'Both', 'Reasoning', or 'Answer'
#         system: 'MAS' or 'SAS'
#         num_agents: Number of agents
#         comparison_type: Type of comparison to plot; 'share-mode' for share mode comparison, 'malicious' for malicious comparison, or 'dataset' for dataset comparison
#     """
#     if comparison_type == 'malicious':
#         categories = ['Wrong→Correct', 'Wrong→Different Wrong', 'Wrong→Same Wrong', 'Correct→Wrong', 'Correct→Correct', 'Wrong→Malicious Wrong', 'Correct→Malicious Wrong']
#     elif comparison_type == 'sharemode_malicious' or comparison_type == 'malicious_convergence':
#         categories = ['Wrong→Correct', 'Wrong→Wrong', 'Correct→Wrong', 'Correct→Correct', 'Converges to Malicious Wrong']

#         datasets_data = {
#             name: stats
#             for name, stats in datasets_data.items()
#             if ("No Mal Agent" not in name and "No Malicious Agent" not in name)
#         }
#     else:
#         categories = ['Wrong→Correct', 'Wrong→Different Wrong', 'Wrong→Same Wrong', 'Correct→Wrong', 'Correct→Correct']
       

    
#     if comparison_type == 'sharemode_malicious' or comparison_type == 'malicious_convergence':
#         fig, ax = plt.subplots(figsize=(22, 7))
#         x = range(len(categories))
#         bar_width = 0.1

#         def dataset_family(name):
#             # Example:
#             # "openai/gsm8k: Mal Agent 1 - Answer" -> "openai/gsm8k"
#             return name.split(':', 1)[0].strip()

#         family_order = []
#         for name in datasets_data.keys():
#             fam = dataset_family(name)
#             if fam not in family_order:
#                 family_order.append(fam)

#         family_colors = seaborn.color_palette("deep", n_colors=max(1, len(family_order)))
#         family_color_map = {fam: family_colors[i] for i, fam in enumerate(family_order)}
#     else:
#         fig, ax = plt.subplots(figsize=(14, 6))
#         x = range(len(categories))
#         bar_width = 0.15 
#         colors = seaborn.color_palette("deep", n_colors=len(datasets_data))
    
    
    
#      # Adjust based on number of datasets
    
#     # Generate color palette for datasets
#     #colors = plt.cm.Set3(range(len(datasets_data)))
#     # colors = seaborn.color_palette("deep", n_colors=len(datasets_data))
    
    
#     for idx, (dataset_name, payload) in enumerate(datasets_data.items()):
#         if isinstance(payload, dict) and "stats" in payload:
#             stats = payload["stats"]
#             num_honest_agents = payload.get("honest_agents", num_agents)
#             # malicious_agents = payload["malicious_agents"]
#         else:
#             stats = payload
#             num_honest_agents = num_agents
#         if comparison_type == 'malicious':
#             counts = [
#                 stats['wrong_correct'],
#                 stats['wrong_different_wrong'],
#                 stats['wrong_same_wrong'],
#                 stats['correct_wrong'],
#                 stats['correct_correct'],
#                 stats['wrong_malicious_wrong'], 
#                 stats['correct_malicious_wrong'],
#             ]
#             percentages = [(count / (stats['num_tasks'] * num_honest_agents)) * 100 for count in counts]
#             # Offset bars for side-by-side display
#             offset = bar_width * idx
#             bars = ax.bar([i + offset for i in x], percentages, bar_width, 
#                         label=dataset_name, color=colors[idx], alpha=0.8)  
#         elif comparison_type == 'sharemode_malicious' or comparison_type == 'malicious_convergence':
#             counts = [
#                 stats['wrong_correct'],
#                 stats['wrong_different_wrong'] + stats['wrong_same_wrong'],
#                 stats['correct_wrong'],
#                 stats['correct_correct'],
#                 stats['wrong_malicious_wrong'] + stats['correct_malicious_wrong']
#             ]
#             print(f"Converges to Malicious Wrong: {stats['wrong_malicious_wrong'] + stats['correct_malicious_wrong']}")

    
#             percentages = [(count / (stats['num_tasks'] * num_honest_agents)) * 100 for count in counts]
#             # Offset bars for side-by-side display
#             offset = bar_width * idx

#             fam = dataset_family(dataset_name)
#             bar_color = family_color_map[fam]

#             name_lower = dataset_name.lower()
#             if 'answer' in name_lower or num_honest_agents == 1:
#                 bar_alpha = 0.45
#             elif 'both' in name_lower or num_honest_agents == 2:
#                 bar_alpha = 0.80
#             else:
#                 bar_alpha = 0.70
                
#             bars = ax.bar([i + offset for i in x], percentages, bar_width, 
#                         label=dataset_name, color=bar_color, alpha=bar_alpha)  
#         else:
#             if "SAS" in dataset_name:
#                 num_agents_update = 1  # For SAS, only 1 agent's answer is relevant for percentage calculation
#             else:
#                 num_agents_update = num_agents  # For MAS, all agents' answers are relevant
#             counts = [
#                 stats['wrong_correct'],
#                 stats['wrong_different_wrong'],
#                 stats['wrong_same_wrong'],
#                 stats['correct_wrong'],
#                 stats['correct_correct']
#             ]
#             percentages = [(count / (stats['num_tasks'] * num_agents_update)) * 100 for count in counts]
#             # Offset bars for side-by-side display
#             offset = bar_width * idx
#             bars = ax.bar([i + offset for i in x], percentages, bar_width, 
#                         label=dataset_name, color=colors[idx], alpha=0.8)
            
#         print(f"type num_tasks {type(stats['num_tasks'])}: {stats['num_tasks']}, type num_agents {type(num_agents)}: {num_agents}")

        
#         # Add percentage labels
#         for bar, percentage in zip(bars, percentages):
#             height = bar.get_height()
#             ax.text(bar.get_x() + bar.get_width()/2., height,
#                    f'{percentage:.1f}%',
#                    ha='center', va='bottom', fontsize=7)
    
#     ax.set_ylabel('Percentage (%) of Tasks')
#     ax.set_xlabel('Answer Pattern')
#     ax.set_ylim(0, 105)
    
#     if comparison_type == 'share-mode':
#         ax.set_title(f'{num_agents} Agents {system}, {model_name}:\n Share-Modes Impact on Answer Patterns')
#     elif comparison_type == 'malicious':
#         ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system} ({num_malicious_agents} Malicious), {model_name}:\n Malicious Agent Impact on Answer Patterns')
#     elif comparison_type == 'sharemode_malicious':
#         ax.set_title(f'{num_agents} Agents {system} ({num_malicious_agents} Malicious), {model_name}:\n Share-Mode and Malicious Agent Impact on Answer Patterns')
#     elif comparison_type == 'malicious_convergence':
#         ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\n Malicious Agent Impact on Answer Pattern Convergence')
#     elif comparison_type == 'model':
#         ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {dataset_filename} dataset:\n Answer Patterns Across Models')    
#     elif comparison_type == 'system':
#         ax.set_title(f'Share-Mode: {share_mode} |  {model_name}, {dataset_filename} dataset:\n Answer Patterns Across Systems')    
#     else:
#         ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\n Answer Patterns Comparison Across Datasets')
    

#     ax.set_xticks([i + bar_width * (len(datasets_data) - 1) / 2 for i in x])
#     ax.set_xticklabels(categories, rotation=45, ha='right')
#     ax.legend()
        
#     plt.tight_layout()
        
#     script_dir = os.path.dirname(os.path.abspath(__file__))
#     output_folder = os.path.join(script_dir, 'statistic_images')
#     os.makedirs(output_folder, exist_ok=True)
    
#     dataset_suffix = '_'.join(datasets_data.keys())

#     if comparison_type == 'share-mode': 
#         plot_image_name = f"{model_name}_{dataset_filename}_{system}_{comparison_type}_comparison_statistics.png"
#     elif comparison_type == 'malicious':
#         plot_image_name = f"{model_name}_{dataset_filename}_{system}_{num_malicious_agents}_comparison_statistics_{share_mode}.png"
#     elif comparison_type == 'sharemode_malicious':
#         plot_image_name = f"{model_name}_{system}_{num_malicious_agents}_{comparison_type}_comparison_statistics.png"
#     elif comparison_type == 'malicious_convergence':
#         plot_image_name = f"{model_name}_{system}_{comparison_type}_comparison_statistics_{share_mode}.png"
#     elif comparison_type == 'model':
#         plot_image_name = f"{dataset_filename}_{system}_{comparison_type}_comparison_statistics_{share_mode}.png"
#     elif comparison_type == 'system':
#         plot_image_name = f"{model_name}_{dataset_filename}_{comparison_type}_comparison_statistics_{share_mode}.png"
#     else:
#         plot_image_name = f"{model_name}_{system}_{comparison_type}_comparison_statistics_{share_mode}.png"
    
#     filepath = os.path.join(output_folder, plot_image_name)
#     plt.savefig(filepath)
#     print(f"Comparison plot saved as {plot_image_name}")

#     # plt.clf()
#     plt.close()


def plot_pattern_statistics_comparison(
    datasets_data,
    model_name,
    dataset_filename='',
    share_mode='Both',
    system='MAS',
    num_agents=3,
    num_malicious_agents=0,
    comparison_type='dataset'
):
    """
    Horizontal version:
    - Percentage on x-axis
    - Answer patterns on y-axis
    - Better for narrow paper columns
    """

    # Categories + optional filtering for malicious comparison families
    if comparison_type == 'malicious':
        categories = [
            'Wrong→Correct',
            'Wrong→Different Wrong',
            'Wrong→Same Wrong',
            'Correct→Wrong',
            'Correct→Correct',
            'Wrong→Malicious Wrong',
            'Correct→Malicious Wrong'
        ]
    elif comparison_type in ('sharemode_malicious', 'malicious_convergence'):
        categories = [
            'Wrong→Correct',
            'Wrong→Wrong',
            'Correct→Wrong',
            'Correct→Correct',
            'Converges to Malicious Wrong'
        ]
        datasets_data = {
            name: payload
            for name, payload in datasets_data.items()
            if ("No Mal Agent" not in name and "No Malicious Agent" not in name)
        }
    else:
        categories = [
            'Wrong→Correct',
            'Wrong→Different Wrong',
            'Wrong→Same Wrong',
            'Correct→Wrong',
            'Correct→Correct'
        ]

    num_sets = max(1, len(datasets_data))
    y_base = list(range(len(categories)))

    # Compact width for paper, adaptive height for readability
    fig_height = max(4.8, 0.85 * len(categories) + 0.18 * num_sets * len(categories))
    fig, ax = plt.subplots(figsize=(10.5, fig_height))

    # Bar thickness per dataset within each category group
    bar_h = min(0.22, 0.8 / num_sets)

    # Color setup
    if comparison_type in ('sharemode_malicious', 'malicious_convergence'):
        def dataset_family(name):
            return name.split(':', 1)[0].strip()

        family_order = []
        for name in datasets_data.keys():
            fam = dataset_family(name)
            if fam not in family_order:
                family_order.append(fam)

        family_colors = seaborn.color_palette("deep", n_colors=max(1, len(family_order)))
        family_color_map = {fam: family_colors[i] for i, fam in enumerate(family_order)}
    else:
        colors = seaborn.color_palette("deep", n_colors=num_sets)

    for idx, (dataset_name, payload) in enumerate(datasets_data.items()):
        if isinstance(payload, dict) and "stats" in payload:
            stats = payload["stats"]
            num_honest_agents = payload.get("honest_agents", num_agents)
        else:
            stats = payload
            num_honest_agents = num_agents

        if comparison_type == 'malicious':
            counts = [
                stats['wrong_correct'],
                stats['wrong_different_wrong'],
                stats['wrong_same_wrong'],
                stats['correct_wrong'],
                stats['correct_correct'],
                stats['wrong_malicious_wrong'],
                stats['correct_malicious_wrong'],
            ]
            denom_agents = num_honest_agents

        elif comparison_type in ('sharemode_malicious', 'malicious_convergence'):
            counts = [
                stats['wrong_correct'],
                stats['wrong_different_wrong'] + stats['wrong_same_wrong'],
                stats['correct_wrong'],
                stats['correct_correct'],
                stats['wrong_malicious_wrong'] + stats['correct_malicious_wrong'],
            ]
            denom_agents = num_honest_agents

        else:
            counts = [
                stats['wrong_correct'],
                stats['wrong_different_wrong'],
                stats['wrong_same_wrong'],
                stats['correct_wrong'],
                stats['correct_correct'],
            ]
            denom_agents = 1 if "SAS" in dataset_name else num_agents

        denom = max(1, stats['num_tasks'] * denom_agents)
        percentages = [(count / denom) * 100 for count in counts]

        # Vertical offset per dataset within each pattern row
        y_offset = (idx - (num_sets - 1) / 2.0) * bar_h
        y_pos = [y + y_offset for y in y_base]

        if comparison_type in ('sharemode_malicious', 'malicious_convergence'):
            fam = dataset_family(dataset_name)
            bar_color = family_color_map[fam]
            name_lower = dataset_name.lower()
            if 'answer' in name_lower or num_honest_agents == 1:
                bar_alpha = 0.45
            elif 'both' in name_lower or num_honest_agents == 2:
                bar_alpha = 0.80
            else:
                bar_alpha = 0.70
            bars = ax.barh(y_pos, percentages, height=bar_h, label=dataset_name, color=bar_color, alpha=bar_alpha)
        else:
            bars = ax.barh(y_pos, percentages, height=bar_h, label=dataset_name, color=colors[idx], alpha=0.8)

        # Value labels at bar end
        for bar, pct in zip(bars, percentages):
            ax.text(
                bar.get_width() + 0.8,
                bar.get_y() + bar.get_height() / 2.0,
                f'{pct:.1f}%',
                va='center',
                ha='left',
                fontsize=6
            )

    ax.set_xlabel('Percentage (%) of Tasks')
    ax.set_ylabel('Answer Pattern')
    ax.set_xlim(0, 105)
    ax.set_yticks(y_base)
    ax.set_yticklabels(categories)
    ax.invert_yaxis()

    if comparison_type == 'share-mode':
        ax.set_title(f'{num_agents} Agents {system}, {model_name}: Share-Modes Impact on Answer Patterns')
    elif comparison_type == 'malicious':
        ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system} ({num_malicious_agents} Malicious), {model_name}:\nMalicious Agent Impact on Answer Patterns')
    elif comparison_type == 'sharemode_malicious':
        ax.set_title(f'{num_agents} Agents {system} ({num_malicious_agents} Malicious), {model_name}:\nShare-Mode and Malicious Agent Impact on Answer Patterns')
    elif comparison_type == 'malicious_convergence':
        ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\nMalicious Convergence Patterns')
    elif comparison_type == 'model':
        ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {dataset_filename}:\nAnswer Patterns Across Models')
    elif comparison_type == 'system':
        ax.set_title(f'Share-Mode: {share_mode} | {model_name}, {dataset_filename}:\nAnswer Patterns Across Systems')
    else:
        ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\nAnswer Patterns Across Datasets')

    # Put legend outside so plot area stays compact
    legend_cols = min(4, num_sets)
    ax.legend(
        loc='upper center',
        bbox_to_anchor=(0.5, -0.14),
        ncol=legend_cols,
        frameon=False,
        fontsize=8
    )
    fig.subplots_adjust(bottom=0.22)
    plt.tight_layout()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, 'statistic_images')
    os.makedirs(output_folder, exist_ok=True)

    if comparison_type == 'share-mode':
        plot_image_name = f"{model_name}_{dataset_filename}_{system}_{comparison_type}_comparison_statistics_horizontal.png"
    elif comparison_type == 'malicious':
        plot_image_name = f"{model_name}_{dataset_filename}_{system}_{num_malicious_agents}_comparison_statistics_{share_mode}_horizontal.png"
    elif comparison_type == 'sharemode_malicious':
        plot_image_name = f"{model_name}_{system}_{num_malicious_agents}_{comparison_type}_comparison_statistics_horizontal.png"
    elif comparison_type == 'malicious_convergence':
        plot_image_name = f"{model_name}_{system}_{comparison_type}_comparison_statistics_{share_mode}_horizontal.png"
    elif comparison_type == 'model':
        plot_image_name = f"{dataset_filename}_{system}_{comparison_type}_comparison_statistics_{share_mode}_horizontal.png"
    elif comparison_type == 'system':
        plot_image_name = f"{model_name}_{dataset_filename}_{comparison_type}_comparison_statistics_{share_mode}_horizontal.png"
    else:
        plot_image_name = f"{model_name}_{system}_{comparison_type}_comparison_statistics_{share_mode}_horizontal.png"

    filepath = os.path.join(output_folder, plot_image_name)
    plt.savefig(filepath, dpi=300, bbox_inches='tight')
    print(f"Comparison plot saved as {plot_image_name}")
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




def calculate_round_statistics(tasks_answers, skip_agents=[], original_task_answers=None, num_agents=3, rounds=3):
    """Calculate round convergence statistics WITHOUT creating a plot. Returns raw counts."""
    wrong_correct = 0
    correct_wrong = 0
    correct_malicious_wrong = 0
    
    num_agents_converge_correct = dict()
    num_agents_converge_wrong = dict()
    num_agents_converge_malicious_wrong = dict()
    
    for round_num in range(1, rounds + 1):
        num_agents_converge_correct[round_num] = num_agents_converge_wrong[round_num] = num_agents_converge_malicious_wrong[round_num] = 0
    num_agents_converge_correct[rounds + 1] = num_agents_converge_wrong[rounds + 1] = num_agents_converge_malicious_wrong[rounds + 1] = 0
    num_agents_converge_correct[rounds + 2] = num_agents_converge_wrong[rounds + 2] = num_agents_converge_malicious_wrong[rounds + 2] = 0

    num_tasks = len(tasks_answers)
    is_converged_to_correct = False
    is_converged_to_wrong = False


    for task_num, (init_answer, round_answers, correct_answer) in tasks_answers.items():
        final_answer = round_answers[rounds + 1]
        malicious_final_answers = []  # Track original answers from skipped agents that changed

        if original_task_answers is not None and task_num in original_task_answers:
            _, original_round_answers, _ = original_task_answers[task_num]
       
            # First pass: identify if any malicious agent changed their answer
            # mal_agent_changes = []  # Track which malicious agents changed
            for agent_idx in skip_agents:
                original_agent_final = original_round_answers[rounds + 1][agent_idx]
                current_agent_final = final_answer[agent_idx]
                
                if current_agent_final != original_agent_final:
                    malicious_final_answers.append(current_agent_final)


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
                    elif wrong_round_answer and not is_converged_to_wrong and round_answer[agent_idx] in malicious_final_answers:
                        num_agents_converge_malicious_wrong[round_num] += 1 
                        num_agents_converge_wrong[round_num] += 1 
                        correct_malicious_wrong += 1
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
        'correct_malicious_wrong': correct_malicious_wrong,
        'num_agents_converge_correct': num_agents_converge_correct,
        'num_agents_converge_wrong': num_agents_converge_wrong,
        'num_agents_converge_malicious_wrong': num_agents_converge_malicious_wrong,
        'num_tasks': num_tasks,
        'num_agents': num_agents,
        'rounds': rounds
    }

# def calculate_round_statistics(tasks_answers, num_agents=3, rounds=3):
#     """Calculate round convergence statistics WITHOUT creating a plot. Returns raw counts."""
#     wrong_correct = 0
#     correct_wrong = 0
    
#     num_agents_converge_correct = dict()
#     num_agents_converge_wrong = dict()
    
#     for round_num in range(1, rounds + 1):
#         num_agents_converge_correct[round_num] = num_agents_converge_wrong[round_num] = 0
#     num_agents_converge_correct[rounds + 1] = num_agents_converge_wrong[rounds + 1] = 0
#     num_agents_converge_correct[rounds + 2] = num_agents_converge_wrong[rounds + 2] = 0

#     num_tasks = len(tasks_answers)
#     is_converged_to_correct = False
#     is_converged_to_wrong = False

#     for task_num, (init_answer, round_answers, correct_answer) in tasks_answers.items():
#         final_answer = round_answers[rounds + 1]

#         for agent_idx, agent_answer in enumerate(zip(init_answer, final_answer)): 
#             init_wrong = agent_answer[0] != correct_answer[0]
#             wrong_to_correct = correct_answer[0] == agent_answer[1]
#             is_converged_to_correct = False 

#             if init_wrong and wrong_to_correct:
#                 wrong_correct += 1

#                 for round_num, round_answer in round_answers.items():
#                     correct_round_answer = round_answer[agent_idx] == correct_answer[0]

#                     if round_num == rounds and not is_converged_to_correct and round_answer[agent_idx] == '':
#                         num_agents_converge_correct[round_num + 2] += 1 
#                         is_converged_to_correct = True
#                         break

#                     elif correct_round_answer and not is_converged_to_correct:
#                         num_agents_converge_correct[round_num] += 1 
#                         is_converged_to_correct = True
#                         break
#                     else:
#                         continue
            
#             is_converged_to_wrong = False

#             if not init_wrong and not wrong_to_correct:
#                 correct_wrong += 1

#                 for round_num, round_answer in round_answers.items():
#                     wrong_round_answer = round_answer[agent_idx] != correct_answer[0]

#                     if round_num == rounds and not is_converged_to_wrong and round_answer[agent_idx] == '':
#                         num_agents_converge_wrong[round_num + 2] += 1 
#                         is_converged_to_wrong = True
#                         break

#                     elif wrong_round_answer and not is_converged_to_wrong:
#                         num_agents_converge_wrong[round_num] += 1 
#                         is_converged_to_wrong = True
#                         break
#                     else:
#                        continue
#     return {
#         'wrong_correct': wrong_correct,
#         'correct_wrong': correct_wrong,
#         'num_agents_converge_correct': num_agents_converge_correct,
#         'num_agents_converge_wrong': num_agents_converge_wrong,
#         'num_tasks': num_tasks,
#         'num_agents': num_agents,
#         'rounds': rounds
#     }


def plot_round_statistics_comparison(datasets_data, model_name, dataset_filename='', share_mode='Both', system="MAS", num_agents=3, rounds=3, num_malicious_agents=0, comparison_type='share-mode'):
    """
    Plot round convergence statistics across multiple datasets side-by-side.
    
    Args:
        datasets_data: Dict like {'openai-gsm8k': stats_dict, 'cais-mmlu': stats_dict, ...}
        model_name: Name of the model (for title/filename)
        share_mode: 'Both', 'Reasoning', or 'Answer'
        system: 'MAS' or 'SAS'
        num_agents: Number of agents
        rounds: Number of rounds
        num_malicious_agents: Number of malicious agents
        comparison_type: Type of comparison to plot; 'share-mode' for share mode comparison, 'malicious' for malicious comparison, or 'dataset' for dataset comparison
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

        if comparison_type == 'malicious':
            correct_wrong = stats['correct_wrong']
            
            if correct_wrong == 0:
                print(f"Warning: {dataset_name} has no 'Correct→Wrong' conversions")
                continue
            
            # Extract convergence counts for each round
            num_agents_converge_wrong = stats['num_agents_converge_wrong']
            round_percentages = [(num_agents_converge_wrong[round_num] / correct_wrong) * 100 
                            for round_num in range(1, rounds + 3)]
            
            # correct_malicious_wrong = stats['correct_malicious_wrong']
            
            # if correct_malicious_wrong == 0:
            #     print(f"Warning: {dataset_name} has no 'Correct→Malicious Wrong' conversions")
            #     continue
            
            # # Extract convergence counts for each round
            # num_agents_converge_malicious_wrong = stats['num_agents_converge_malicious_wrong']
            # round_percentages_malicious = [(num_agents_converge_malicious_wrong[round_num] / correct_malicious_wrong) * 100 
            #                 for round_num in range(1, rounds + 3)]
    
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

    if comparison_type == 'malicious':    
        ax.set_ylabel('Percentage (%) of Correct→Wrong Answer Tasks')
        ax.set_xlabel('Round')
        ax.set_ylim(0, 105)
        ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system} ({num_malicious_agents} Malicious), {model_name}:\n Convergence From Correct→Wrong Answer')
    elif comparison_type == 'share-mode':
        ax.set_ylabel('Percentage (%) of Wrong→Correct Answer Tasks')
        ax.set_xlabel('Round')
        ax.set_ylim(0, 105)
        ax.set_title(f'{num_agents} Agents {system}, {model_name}:\n Convergence From Wrong→Correct Answer')
    else:
        ax.set_ylabel('Percentage (%) of Wrong→Correct Answer Tasks')
        ax.set_xlabel('Round')
        ax.set_ylim(0, 105)
        ax.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system}, {model_name}:\n Convergence From Wrong→Correct Answer')

    ax.set_xticks([i + bar_width * (len(datasets_data) - 1) / 2 for i in x])
    ax.set_xticklabels(round_categories, rotation=45, ha='right')
    ax.legend()
        
    plt.tight_layout()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, 'statistic_images')
    os.makedirs(output_folder, exist_ok=True)   

    if comparison_type == 'malicious': 
        filepath = os.path.join(output_folder, f"{model_name}_{system}_{dataset_filename}_{num_malicious_agents}{comparison_type}_comparison_round_statistics_{share_mode}.png")
        plt.savefig(filepath)
        print(f"Comparison round plot saved as {model_name}_{system}_{dataset_filename}_{num_malicious_agents}{comparison_type}_comparison_round_statistics_{share_mode}.png")
    elif comparison_type == 'share-mode':
        filepath = os.path.join(output_folder, f"{model_name}_{system}_{dataset_filename}_{comparison_type}_comparison_round_statistics.png")
        plt.savefig(filepath)
        print(f"Comparison round plot saved as {model_name}_{system}_{dataset_filename}_{comparison_type}_comparison_round_statistics.png")
    else:
        filepath = os.path.join(output_folder, f"{model_name}_{system}_{comparison_type}_comparison_round_statistics_{share_mode}.png")
        plt.savefig(filepath)
        print(f"Comparison round plot saved as {model_name}_{system}_{comparison_type}_comparison_round_statistics_{share_mode}.png")
    plt.close()

def plot_malicious_round_statistics_comparison(datasets_data, model_name, dataset_filename='', share_mode='Both', system="MAS", num_agents=3, rounds=3, num_malicious_agents=0):
    """
    Plot round convergence statistics across multiple datasets side-by-side.
    
    Args:
        datasets_data: Dict like {'openai-gsm8k': stats_dict, 'cais-mmlu': stats_dict, ...}
        model_name: Name of the model (for title/filename)
        share_mode: 'Both', 'Reasoning', or 'Answer'
        system: 'MAS' or 'SAS'
        num_agents: Number of agents
        rounds: Number of rounds
        num_malicious_agents: Number of malicious agents

    """
    # Build round categories
    round_categories = []
    for round_num in range(1, rounds + 1):
        round_categories.append(f'Round {round_num}')
    round_categories.append(f'Final Answer')
    round_categories.append(f'Unknown\nConvergence\nRound')
    
    fig, ax = plt.subplots(figsize=(14, 6))

    fig2, ax2 = plt.subplots(figsize=(14, 6))
    
    x = range(len(round_categories))
    bar_width = 0.15
    
    # Generate color palette for datasets
    #colors = plt.cm.Set3(range(len(datasets_data)))
    colors = seaborn.color_palette("deep", n_colors=len(datasets_data))
    
    for idx, (dataset_name, stats) in enumerate(datasets_data.items()):

        correct_wrong = stats['correct_wrong']
        
        if correct_wrong == 0:
            print(f"Warning: {dataset_name} has no 'Correct→Wrong' conversions")
            continue
        
        # Extract convergence counts for each round
        num_agents_converge_wrong = stats['num_agents_converge_wrong']
        round_percentages = [(num_agents_converge_wrong[round_num] / correct_wrong) * 100 
                        for round_num in range(1, rounds + 3)]
        
        correct_malicious_wrong = stats['correct_malicious_wrong']
        
        # Calculate malicious percentages (zero if no malicious conversions)
        if correct_malicious_wrong > 0:
            num_agents_converge_malicious_wrong = stats['num_agents_converge_malicious_wrong']
            round_percentages_malicious = [(num_agents_converge_malicious_wrong[round_num] / correct_wrong) * 100 
                            for round_num in range(1, rounds + 3)]
        else:
            round_percentages_malicious = [0.0] * (rounds + 2)

        # Offset bars for side-by-side display
        offset = bar_width * idx
        bars = ax.bar([i + offset for i in x], round_percentages, bar_width, 
                    label=dataset_name, color=colors[idx], alpha=0.8)
        
        # Add percentage labels to first plot
        for bar, percentage in zip(bars, round_percentages):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{percentage:.1f}%',
                ha='center', va='bottom', fontsize=7)

        # Plot both series on ax2
        correct_bars = ax2.bar(
            [i + offset for i in x],
            round_percentages,
            bar_width,
            label=f"{dataset_name} Correct→Wrong",
            color=colors[idx],
            alpha=0.9
        )

        # Add percentage labels for Correct→Wrong bars
        for bar, percentage in zip(correct_bars, round_percentages):
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{percentage:.1f}%",
                ha='center',
                va='bottom',
                fontsize=7
            )

        # Only plot malicious bars for non-baseline datasets
        if 'No' not in dataset_name:
            malicious_bars = ax2.bar(
                [i + offset for i in x],
                round_percentages_malicious,
                bar_width,
                label=f"{dataset_name} Correct→Malicious Wrong",
                color=colors[idx],
                alpha=0.9,
                hatch='//',
                edgecolor='black',
                linewidth=0.8
            )

            for bar, percentage in zip(malicious_bars, round_percentages_malicious):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{percentage:.1f}%",
                    ha='center',
                    va='bottom',
                    fontsize=7
                )
 
    ax2.set_ylabel('Percentage (%) of Correct→MaliciousWrong Answer Tasks')
    ax2.set_xlabel('Round')
    ax2.set_ylim(0, 105)
    ax2.set_title(f'Share-Mode: {share_mode} | {num_agents} Agents {system} ({num_malicious_agents} Malicious), {model_name}:\n Convergence From Correct→ Malicious Wrong Answer')

    ax2.set_xticks([i + bar_width * (len(datasets_data) - 1) / 2 for i in x])
    ax2.set_xticklabels(round_categories, rotation=45, ha='right')
    ax2.legend()
        
    fig2.tight_layout()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_folder = os.path.join(script_dir, 'statistic_images')
    os.makedirs(output_folder, exist_ok=True)   

   
    filepath_mal = os.path.join(output_folder, f"{model_name}_{system}_{dataset_filename}_{num_malicious_agents}_comparison_round_statistics_maliciouswrong_{share_mode}.png")
    fig2.savefig(filepath_mal)
    print(f"Comparison round plot saved as {model_name}_{system}_{dataset_filename}_{num_malicious_agents}_comparison_round_statistics_maliciouswrong_{share_mode}.png")
    plt.close(fig2)


def dataset_comparison(transcripts, round_figure=False, comparison_type='dataset'):
    """
    Main function to perform dataset comparison for a given model and share mode.
    
    Args:
        transcripts: Dict like {'openai-gsm8k': 'path/to/transcripts', 'cais-mmlu': 'path/to/transcripts', ...}
        dataset_name: Name of the specific dataset (for title/filename)
        share_mode: 'Both', 'Reasoning', or 'Answer'
        system: 'MAS' or 'SAS'
        num_agents: Number of agents involved in the simulation
        rounds: Number of rounds in the simulation
    """
    datasets_data = dict()
    num_agents = None
    num_rounds = None
    share_mode = ""
    dataset_filename = ""

    if round_figure:
        datasets_data_round = dict()
 
    for dataset_name, transcript_path in transcripts.items():
        # Extract answers for each dataset
        answers, round_answers, summary_info = extract_answers(transcript_path)
        num_agents = summary_info['num_agents']
        print(f"num agents type after being extacted from summary_info: {type(num_agents)}, num_agents: {num_agents}")
        num_rounds = summary_info['num_rounds']
        share_mode = summary_info['share_mode']
        dataset_filename = summary_info['dataset_filename']
        system = summary_info['system']
        model_name = summary_info['model_name']

        # Calculate statistics for each dataset
        stats = calculate_pattern_statistics(answers)
        if round_figure:
            round_stats = calculate_round_statistics(round_answers, num_agents=num_agents, rounds=num_rounds)
            datasets_data_round[dataset_name] = round_stats
        # Store statistics for comparison
        datasets_data[dataset_name] = stats
    
    plot_pattern_statistics_comparison(
        datasets_data,
        model_name,
        dataset_filename=dataset_filename,
        share_mode=share_mode,
        system=system,
        num_agents=num_agents,
        comparison_type=comparison_type,
    )
    if round_figure:
        plot_round_statistics_comparison(
            datasets_data_round,
            model_name,
            dataset_filename=dataset_filename,
            share_mode=share_mode,
            system=system,
            num_agents=num_agents,
            rounds=num_rounds,
            comparison_type=comparison_type,
        )



def malicious_comparison(transcripts, round_figure=True, comparison_type='malicious'):
    datasets_data = {}
    datasets_data_round = {}

    baseline_answers = None
    baseline_round_answers = None
    malicious_agents = []
    num_agents = num_rounds = None
    share_mode = dataset_filename = system = model_name = ""

    for dataset_name, transcript_path in transcripts.items():
        answers, round_answers, summary_info = extract_answers(transcript_path)

        num_rounds = summary_info['num_rounds']
        share_mode = summary_info['share_mode']
        dataset_filename = summary_info['dataset_filename']
        system = summary_info['system']
        model_name = summary_info['model_name']
        num_agents = summary_info['num_agents']

        if 'No' in dataset_name:
            
            baseline_answers = answers
            baseline_round_answers = round_answers

        
            datasets_data[dataset_name] = {
            "stats": calculate_pattern_statistics(
                baseline_answers,
                skip_agents=[],
                original_task_answers=None,
            ),
            "honest_agents": num_agents,  # baseline
            # "malicious_agents": 0
            }           

            if round_figure:
                datasets_data_round[dataset_name] = calculate_round_statistics(
                    baseline_round_answers,
                    skip_agents=[],
                    original_task_answers=None,
                    num_agents=num_agents,
                    rounds=num_rounds,
                )
        else:
            malicious_agents = summary_info['malicious_agents']
       
            datasets_data[dataset_name] = {
                "stats": calculate_pattern_statistics(
                answers,
                skip_agents=malicious_agents,
                original_task_answers=baseline_answers,
                ),
                "honest_agents": num_agents - len(malicious_agents),  # malicious run
                # "malicious_agents": malicious_agents
            }

            if round_figure:
                datasets_data_round[dataset_name] = calculate_round_statistics(
                    round_answers,
                    skip_agents=malicious_agents,
                    original_task_answers=baseline_round_answers,
                    num_agents=num_agents - len(malicious_agents),
                    rounds=num_rounds,
                )
                
    print(datasets_data)

    plot_pattern_statistics_comparison(
        datasets_data,
        model_name,
        dataset_filename=dataset_filename,
        share_mode=share_mode,
        system=system,
        num_agents=num_agents,
        num_malicious_agents=len(malicious_agents),
        comparison_type=comparison_type,
    )

    if round_figure:
        plot_malicious_round_statistics_comparison(
            datasets_data_round,
            model_name,
            dataset_filename=dataset_filename,
            share_mode=share_mode,
            system=system,
            num_agents=num_agents,
            rounds=num_rounds,
            num_malicious_agents=len(malicious_agents),
        )



# transcript_data = {
#     'openai/gsm8k No Malicious Agent': 'transcripts_mal_test/qwen3b_2026-03-29_00h31m15s',
#     'openai/gsm8k Malicious Agent 3': 'transcripts_mal_test/qwen3b_job342_2026-04-01_01h15m49s',
#     'openai/gsm8k No Malicious Agent again': 'transcripts_mal_test/qwen3b_2026-03-29_00h31m15s',
#     'openai/gsm8k Malicious Agent 2': 'transcripts_mal_test/qwen3b_job342_2026-04-01_01h15m49s'
# }

# malicious_comparison(transcript_data, round_figure=True)
# dataset_comparison(transcript_data, round_figure=True, comparison_type='malicious')

# ╔════════════════════════════════════════╗
# ║           DATASET COMPARISONS          ║
# ╚════════════════════════════════════════╝

# ------ Comparison between different datasets, QWEN, both, MAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
#     'cais/mmlu': 'transcripts/MAS/both/qwen3b_2026-03-29_15h34m56s',
#     'ChilleD/StrategyQA': 'transcripts/MAS/both/qwen3b_2026-03-29_15h26m25s',
#     'tasksource/bigbench': 'transcripts/MAS/both/qwen3b_2026-03-29_03h35m18s'
# }
# dataset_comparison(transcript_data, round_figure=True)

# # ------ Comparison between different datasets, Olmo, both, MAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/MAS/both/olmo7b_2026-03-29_15h41m56s',
#     'cais/mmlu': 'transcripts/MAS/both/olmo7b_2026-03-29_15h29m53s',
#     'ChilleD/StrategyQA': 'transcripts/MAS/both/olmo7b_2026-03-29_15h26m25s',
#     'tasksource/bigbench': 'transcripts/MAS/both/olmo7b_2026-03-29_01h47m46s'
# }
# dataset_comparison(transcript_data, round_figure=True)

# # ------ Comparison between different datasets, Llama, both, MAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/MAS/both/llama3b_2026-03-29_15h19m52s',
#     'cais/mmlu': 'transcripts/MAS/both/llama3b_2026-03-29_00h34m49s',
#     'ChilleD/StrategyQA': 'transcripts/MAS/both/llama3b_2026-03-29_15h21m49s',
#     'tasksource/bigbench': 'transcripts/MAS/both/llama3b_2026-03-29_03h08m47s'
# }
# dataset_comparison(transcript_data, round_figure=True)

# # ------ Comparison between different datasets, QWEN, both, SAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/SAS/both/qwen3b_job9712_2026-03-30_22h08m41s',
#     'cais/mmlu': 'transcripts/SAS/both/qwen3b_job9713_2026-03-30_22h10m26s',
#     'ChilleD/StrategyQA': 'transcripts/SAS/both/qwen3b_job9714_2026-03-30_22h12m15s',
#     'tasksource/bigbench': 'transcripts/SAS/both/qwen3b_job9715_2026-03-30_22h13m45s'
# }
# dataset_comparison(transcript_data, round_figure=True)

# # ------ Comparison between different datasets, Olmo, both, SAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/SAS/both/olmo7b_job9749_2026-03-31_00h58m55s',
#     'cais/mmlu': 'transcripts/SAS/both/olmo7b_job9750_2026-03-31_00h59m14s',
#     'ChilleD/StrategyQA': 'transcripts/SAS/both/olmo7b_job9751_2026-03-31_00h59m43s',
#     'tasksource/bigbench': 'transcripts/SAS/both/olmo7b_job9790_2026-03-31_09h14m42s'
# }
# dataset_comparison(transcript_data, round_figure=True)

# # ------ Comparison between different datasets, llama, both, SAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/SAS/both/llama3b_job9794_2026-03-31_09h18m03s',
#     'cais/mmlu': 'transcripts/SAS/both/llama3b_job9793_2026-03-31_09h18m03s',
#     'ChilleD/StrategyQA': 'transcripts/SAS/both/llama3b_job9792_2026-03-31_09h16m56s',
#     'tasksource/bigbench': 'transcripts/SAS/both/llama3b_job9791_2026-03-31_09h16m39s'
# }
# dataset_comparison(transcript_data, round_figure=True)


# ╔════════════════════════════════════════╗
# ║         SHARE-MODE COMPARISONS         ║
# ╚════════════════════════════════════════╝

# # --- share-mode comparison for Qwen ---
# transcript_data = {
#     'openai/gsm8k: Both Share-mode': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
#     'openai/gsm8k: Reasoning Share-mode': 'transcripts/MAS/reasoning/qwen3b_job9706_2026-03-30_22h01m46s',
#     'openai/gsm8k: Answer Share-mode': 'transcripts/MAS/answer/qwen3b_job9705_2026-03-30_21h58m14s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# transcript_data = {
#     'cais/mmlu: Both Share-mode': 'transcripts/MAS/both/qwen3b_2026-03-29_15h34m56s',
#     'cais/mmlu: Reasoning Share-mode': 'transcripts/MAS/reasoning/qwen3b_job9913_2026-03-31_11h56m29s',
#     'cais/mmlu: Answer Share-mode': 'transcripts/MAS/answer/qwen3b_job9914_2026-03-31_11h56m37s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# transcript_data = {
#     'ChilleD/StrategyQA: Both Share-mode': 'transcripts/MAS/both/qwen3b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Reasoning Share-mode': 'transcripts/MAS/reasoning/qwen3b_job9917_2026-03-31_12h00m28s',
#     'ChilleD/StrategyQA: Answer Share-mode': 'transcripts/MAS/answer/qwen3b_job9918_2026-03-31_17h05m39s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# transcript_data = {
#     'tasksource/bigbench both': 'transcripts/MAS/both/qwen3b_2026-03-29_03h35m18s',
#     'tasksource/bigbench reasoning': 'transcripts/MAS/reasoning/qwen3b_2026-03-29_21h37m18s',
#     'tasksource/bigbench answer': 'transcripts/MAS/answer/qwen3b_2026-03-29_21h46m31s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# # --- share-mode comparison for Olmo ---
# transcript_data = {
#     'openai/gsm8k: Both Share-mode': 'transcripts/MAS/both/olmo7b_2026-03-29_15h41m56s',
#     'openai/gsm8k: Reasoning Share-mode': 'transcripts/MAS/reasoning/olmo7b_job125_2026-03-31_19h35m18s',
#     'openai/gsm8k: Answer Share-mode': 'transcripts/MAS/answer/olmo7b_job126_2026-03-31_19h41m31s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# transcript_data = {
#     'cais/mmlu: Both Share-mode': 'transcripts/MAS/both/olmo7b_2026-03-29_15h29m53s',
#     'cais/mmlu: Reasoning Share-mode': 'transcripts/MAS/reasoning/olmo7b_job123_2026-03-31_19h08m02s',
#     'cais/mmlu: Answer Share-mode': 'transcripts/MAS/answer/olmo7b_job124_2026-03-31_19h08m18s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# transcript_data = {
#     'ChilleD/StrategyQA: Both Share-mode': 'transcripts/MAS/both/olmo7b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Reasoning Share-mode': 'transcripts/MAS/reasoning/olmo7b_job9972_2026-03-31_17h42m46s',
#     'ChilleD/StrategyQA: Answer Share-mode': 'transcripts/MAS/answer/olmo7b_job9973_2026-03-31_18h08m36s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# transcript_data = {
#     'tasksource/bigbench: Both Share-mode': 'transcripts/MAS/both/olmo7b_2026-03-29_01h47m46s',
#     'tasksource/bigbench: Reasoning Share-mode': 'transcripts/MAS/reasoning/olmo7b_2026-03-29_21h37m22s',
#     'tasksource/bigbench: Answer Share-mode': 'transcripts/MAS/answer/olmo7b_2026-03-29_21h46m31s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# # --- share-mode comparison for Llama ---
# transcript_data = {
#     'openai/gsm8k: Both Share-mode': 'transcripts/MAS/both/llama3b_2026-03-29_15h19m52s',
#     'openai/gsm8k: Reasoning Share-mode': 'transcripts/MAS/reasoning/llama3b_job9703_2026-03-30_21h56m07s',
#     'openai/gsm8k: Answer Share-mode': 'transcripts/MAS/answer/llama3b_job9704_2026-03-30_21h57m33s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# transcript_data = {
#     'cais/mmlu: Both Share-mode': 'transcripts/MAS/both/llama3b_2026-03-29_00h34m49s',
#     'cais/mmlu: Reasoning Share-mode': 'transcripts/MAS/reasoning/llama3b_job348_2026-04-01_03h40m36s',
#     'cais/mmlu: Answer Share-mode': 'transcripts/MAS/answer/llama3b_job349_2026-04-01_04h00m41s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# transcript_data = {
#     'ChilleD/StrategyQA: Both Share-mode': 'transcripts/MAS/both/llama3b_2026-03-29_15h21m49s',
#     'ChilleD/StrategyQA: Reasoning Share-mode': 'transcripts/MAS/reasoning/llama3b_job350_2026-04-01_05h03m45s',
#     'ChilleD/StrategyQA: Answer Share-mode': 'transcripts/MAS/answer/llama3b_job351_2026-04-01_07h39m19s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')

# transcript_data = {
#     'tasksource/bigbench: Both Share-mode': 'transcripts/MAS/both/llama3b_2026-03-29_03h08m47s',
#     'tasksource/bigbench: Reasoning Share-mode': 'transcripts/MAS/reasoning/llama3b_2026-03-29_21h37m45s',
#     'tasksource/bigbench: Answer Share-mode': 'transcripts/MAS/answer/llama3b_2026-03-29_23h24m02s'
# }
# dataset_comparison(transcript_data, comparison_type='share-mode')


# ╔════════════════════════════════════════╗
# ║       MALICIOUS PROMPT COMPARISONS     ║
# ╚════════════════════════════════════════╝

# # --- Malicious prompt comparison for Qwen ---
# transcript_data = {
#     'tasksource/bigbench: No Mal Agent - both': 'transcripts/MAS/both/qwen3b_2026-03-29_03h35m18s',
#     'tasksource/bigbench: Mal Agent 1 - both': 'transcripts/MAS/malicious/bigbench/qwen3b_job9921_2026-03-31_13h53m46s',
#     'tasksource/bigbench: Mal Agent 3 - both': 'transcripts/MAS/malicious/bigbench/qwen3b_job9925_2026-03-31_16h22m36s',
# }
# malicious_comparison(transcript_data, round_figure=False)

# transcript_data = {
#     'tasksource/bigbench: No Mal Agent - answer': 'transcripts/MAS/answer/qwen3b_2026-03-29_21h46m31s',
#     'tasksource/bigbench: Mal Agent 1 - answer': 'transcripts/MAS/malicious/bigbench/qwen3b_job9929_2026-03-31_16h56m02s',
#     'tasksource/bigbench: Mal Agent 3 - answer': 'transcripts/MAS/malicious/bigbench/qwen3b_job337_2026-04-01_01h00m42s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Olmo ---
# transcript_data = {
#     'tasksource/bigbench: No Mal Agent - both': 'transcripts/MAS/both/olmo7b_2026-03-29_01h47m46s',
#     'tasksource/bigbench: Mal Agent 1 - both': 'transcripts/MAS/malicious/bigbench/olmo7b_job9922_2026-03-31_15h39m15s',
#     'tasksource/bigbench: Mal Agent 3 - both': 'transcripts/MAS/malicious/bigbench/olmo7b_job347_2026-04-01_03h38m14s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'tasksource/bigbench: No Mal Agent - answer': 'transcripts/MAS/answer/olmo7b_job126_2026-03-31_19h41m31s',
#     'tasksource/bigbench: Mal Agent 1 - answer': 'transcripts/MAS/malicious/bigbench/olmo7b_job9930_2026-03-31_16h57m17s',
#     'tasksource/bigbench: Mal Agent 3 - answer': 'transcripts/MAS/malicious/bigbench/olmo7b_job338_2026-04-01_01h02m15s',
# }
# malicious_comparison(transcript_data)


# # # --- Malicious prompt comparison for Llama ---
# transcript_data = {
#     'tasksource/bigbench: No Mal Agent - both': 'transcripts/MAS/both/llama3b_2026-03-29_03h08m47s',
#     'tasksource/bigbench: Mal Agent 1 - both': 'transcripts/MAS/malicious/bigbench/llama3b_job9920_2026-03-31_12h08m05s',
#     'tasksource/bigbench: Mal Agent 3 - both': 'transcripts/MAS/malicious/bigbench/llama3b_job9924_2026-03-31_16h17m31s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'tasksource/bigbench: No Mal Agent - answer': 'transcripts/MAS/answer/llama3b_2026-03-29_23h24m02s',
#     'tasksource/bigbench: Mal Agent 1 - answer': 'transcripts/MAS/malicious/bigbench/llama3b_job9928_2026-03-31_16h55m27s',
#     'tasksource/bigbench: Mal Agent 3 - answer': 'transcripts/MAS/malicious/bigbench/llama3b_job336_2026-04-01_01h00m20s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Qwen ---
# transcript_data = {
#     'openai/gsm8k: No Mal Agent - both': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
#     'openai/gsm8k: Mal Agent 1 - both': 'transcripts/MAS/malicious/gsm8k/qwen3b_job345_2026-04-01_01h35m32s',
#     'openai/gsm8k: Mal Agent 3 - both': 'transcripts/MAS/malicious/gsm8k/qwen3b_job342_2026-04-01_01h15m49s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'openai/gsm8k: No Mal Agent - answer': 'transcripts/MAS/answer/qwen3b_job9705_2026-03-30_21h58m14s',
#     'openai/gsm8k: Mal Agent 1 - answer': 'transcripts/MAS/malicious/gsm8k/qwen3b_job3963_2026-04-02_02h14m14s',
#     'openai/gsm8k: Mal Agent 3 - answer': 'transcripts/MAS/malicious/gsm8k/qwen3b_job3960_2026-04-01_16h46m12s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Olmo ---
# transcript_data = {
#     'openai/gsm8k: No Mal Agent - both': 'transcripts/MAS/both/olmo7b_2026-03-29_15h41m56s',
#     'openai/gsm8k: Mal Agent 1 - both': 'transcripts/MAS/malicious/gsm8k/olmo7b_job346_2026-04-01_02h18m18s',
#     'openai/gsm8k: Mal Agent 3 - both': 'transcripts/MAS/malicious/gsm8k/olmo7b_job343_2026-04-01_01h15m49s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'openai/gsm8k: No Mal Agent - answer': 'transcripts/MAS/answer/olmo7b_job126_2026-03-31_19h41m31s',
#     'openai/gsm8k: Mal Agent 1 - answer': 'transcripts/MAS/malicious/gsm8k/olmo7b_job3964_2026-04-02_04h05m45s',
#     'openai/gsm8k: Mal Agent 3 - answer': 'transcripts/MAS/malicious/gsm8k/olmo7b_job3961_2026-04-01_23h51m40s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Llama ---
# transcript_data = {
#     'openai/gsm8k: No Mal Agent - both': 'transcripts/MAS/both/llama3b_2026-03-29_15h19m52s',
#     'openai/gsm8k: Mal Agent 1 - both': 'transcripts/MAS/malicious/gsm8k/llama3b_job344_2026-04-01_01h21m12s',
#     'openai/gsm8k: Mal Agent 3 - both': 'transcripts/MAS/malicious/gsm8k/llama3b_job341_2026-04-01_01h15m43s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'openai/gsm8k: No Mal Agent - answer': 'transcripts/MAS/answer/llama3b_job9704_2026-03-30_21h57m33s',
#     'openai/gsm8k: Mal Agent 1 - answer': 'transcripts/MAS/malicious/gsm8k/llama3b_job3962_2026-04-02_01h48m51s',
#     'openai/gsm8k: Mal Agent 3 - answer': 'transcripts/MAS/malicious/gsm8k/llama3b_job3959_2026-04-01_15h52m13s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Qwen ---
# transcript_data = {
#     'cais/mmlu: No Mal Agent - both': 'transcripts/MAS/both/qwen3b_2026-03-29_15h34m56s',
#     'cais/mmlu: Mal Agent 1 - both': 'transcripts/MAS/malicious/mmlu/qwen3b_job4470_2026-04-02_08h10m34s',
#     'cais/mmlu: Mal Agent 3 - both': 'transcripts/MAS/malicious/mmlu/qwen3b_job4466_2026-04-02_04h47m13s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'cais/mmlu: No Mal Agent - answer': 'transcripts/MAS/answer/qwen3b_job9914_2026-03-31_11h56m37s',
#     'cais/mmlu: Mal Agent 1 - answer': 'transcripts/MAS/malicious/mmlu/qwen3b_job7400_2026-04-03_01h36m45s',
#     'cais/mmlu: Mal Agent 3 - answer': 'transcripts/MAS/malicious/mmlu/qwen3b_job7403_2026-04-03_06h42m02s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Olmo ---
# transcript_data = {
#     'cais/mmlu: No Mal Agent - both': 'transcripts/MAS/both/olmo7b_2026-03-29_15h29m53s',
#     'cais/mmlu: Mal Agent 1 - both': 'transcripts/MAS/malicious/mmlu/olmo7b_job4471_2026-04-02_08h10m34s',
#     'cais/mmlu: Mal Agent 3 - both': 'transcripts/MAS/malicious/mmlu/olmo7b_job4467_2026-04-02_08h10m34s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'cais/mmlu: No Mal Agent - answer': 'transcripts/MAS/answer/olmo7b_job124_2026-03-31_19h08m18s',
#     'cais/mmlu: Mal Agent 1 - answer': 'transcripts/MAS/malicious/mmlu/olmo7b_job7401_2026-04-03_05h19m55s',
#     'cais/mmlu: Mal Agent 3 - answer': 'transcripts/MAS/malicious/mmlu/olmo7b_job7404_2026-04-03_07h25m56s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Llama ---
# transcript_data = {
#     'cais/mmlu: No Mal Agent - both': 'transcripts/MAS/both/llama3b_2026-03-29_00h34m49s',
#     'cais/mmlu: Mal Agent 1 - both': 'transcripts/MAS/malicious/mmlu/llama3b_job4469_2026-04-02_08h10m34s',
#     'cais/mmlu: Mal Agent 3 - both': 'transcripts/MAS/malicious/mmlu/llama3b_job4465_2026-04-02_04h34m10s',
# }
# malicious_comparison(transcript_data)

# # --- Malicious prompt comparison for Llama ---
# transcript_data = {
#     'cais/mmlu: No Mal Agent - answer': 'transcripts/MAS/answer/llama3b_job349_2026-04-01_04h00m41s',
#     'cais/mmlu: Mal Agent 1 - answer': 'transcripts/MAS/malicious/mmlu/llama3b_job7399_2026-04-03_01h36m45s',
#     'cais/mmlu: Mal Agent 3 - answer': 'transcripts/MAS/malicious/mmlu/llama3b_job7402_2026-04-03_05h21m13s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Qwen ---
# transcript_data = {
#     'ChilleD/StrategyQA: No Mal Agent - both': 'transcripts/MAS/both/qwen3b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Mal Agent 1 - both': 'transcripts/MAS/malicious/strategyQA/qwen3b_job7394_2026-04-03_01h31m22s',
#     'ChilleD/StrategyQA: Mal Agent 3 - both': 'transcripts/MAS/malicious/strategyQA/qwen3b_job7384_2026-04-03_01h14m27s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'ChilleD/StrategyQA: No Mal Agent - answer': 'transcripts/MAS/answer/qwen3b_job9918_2026-03-31_17h05m39s',
#     'ChilleD/StrategyQA: Mal Agent 1 - answer': 'transcripts/MAS/malicious/strategyQA/qwen3b_job7387_2026-04-03_01h15m56s',
#     'ChilleD/StrategyQA: Mal Agent 3 - answer': 'transcripts/MAS/malicious/strategyQA/qwen3b_job7904_2026-04-04_02h02m06s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Olmo ---
# transcript_data = {
#     'ChilleD/StrategyQA: No Mal Agent - both': 'transcripts/MAS/both/olmo7b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Mal Agent 1 - both': 'transcripts/MAS/malicious/strategyQA/olmo7b_job7395_2026-04-03_01h30m38s',
#     'ChilleD/StrategyQA: Mal Agent 3 - both': 'transcripts/MAS/malicious/strategyQA/olmo7b_job7385_2026-04-03_01h15m54s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'ChilleD/StrategyQA: No Mal Agent - answer': 'transcripts/MAS/answer/olmo7b_job9973_2026-03-31_18h08m36s',
#     'ChilleD/StrategyQA: Mal Agent 1 - answer': 'transcripts/MAS/malicious/strategyQA/olmo7b_job7388_2026-04-03_01h15m54s',
#     'ChilleD/StrategyQA: Mal Agent 3 - answer': 'transcripts/MAS/malicious/strategyQA/olmo7b_job7905_2026-04-04_02h02m06s',
# }
# malicious_comparison(transcript_data)


# # --- Malicious prompt comparison for Llama ---
# transcript_data = {
#     'ChilleD/StrategyQA: No Mal Agent - both': 'transcripts/MAS/both/llama3b_2026-03-29_15h21m49s',
#     'ChilleD/StrategyQA: Mal Agent 1 - both': 'transcripts/MAS/malicious/strategyQA/llama3b_job7393_2026-04-03_01h31m22s',
#     'ChilleD/StrategyQA: Mal Agent 3 - both': 'transcripts/MAS/malicious/strategyQA/llama3b_job7396_2026-04-03_01h30m38s',
# }
# malicious_comparison(transcript_data)

# transcript_data = {
#     'ChilleD/StrategyQA: No Mal Agent - answer': 'transcripts/MAS/answer/llama3b_job351_2026-04-01_07h39m19s',
#     'ChilleD/StrategyQA: Mal Agent 1 - answer': 'transcripts/MAS/malicious/strategyQA/llama3b_job7386_2026-04-03_01h15m52s',
#     'ChilleD/StrategyQA: Mal Agent 3 - answer': 'transcripts/MAS/malicious/strategyQA/llama3b_job7903_2026-04-04_02h02m06s',
# }
# malicious_comparison(transcript_data)


# ╔═════════════════════════════════════════════════╗
# ║       2 MALICIOUS AGENTS PROMPT COMPARISONS     ║
# ╚═════════════════════════════════════════════════╝

            # # --- Malicious prompt comparison for Llama ---
            # transcript_data = {
            #     'tasksource/bigbench: No Mal Agent': 'transcripts/MAS/both/llama3b_2026-03-29_03h08m47s',
            #     'tasksource/bigbench: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/bigbench/llama3b_job7928_2026-04-04_06h09m05s',
            #     'tasksource/bigbench: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/bigbench/llama3b_job1759_2026-04-10_15h44m06s',
            #     'tasksource/bigbench: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/bigbench/llama3b_job1756_2026-04-10_15h29m06s',
            #     # 'tasksource/bigbench: No Mal Agent - answer': 'transcripts/MAS/answer/llama3b_2026-03-29_23h24m02s',
            #     # 'tasksource/bigbench: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/bigbench/llama3b_job8617_2026-04-05_12h39m22s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)

            # # --- Malicious prompt comparison for Olmo ---
            # transcript_data = {
            #     'tasksource/bigbench: No Mal Agent': 'transcripts/MAS/both/olmo7b_2026-03-29_01h47m46s',
            #     'tasksource/bigbench: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/bigbench/olmo7b_job7930_2026-04-04_11h15m30s',
            #     'tasksource/bigbench: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/bigbench/olmo7b_job1761_2026-04-10_15h46m50s',
            #     'tasksource/bigbench: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/bigbench/olmo7b_job1758_2026-04-10_15h44m06s',
            #     # 'tasksource/bigbench: No Mal Agent - answer': 'transcripts/MAS/answer/olmo7b_job126_2026-03-31_19h41m31s',
            #     # 'tasksource/bigbench: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/bigbench/olmo7b_job8619_2026-04-05_12h39m23s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)

            # # --- Malicious prompt comparison for Qwen ---
            # transcript_data = {
            #     'tasksource/bigbench: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_03h35m18s',
            #     'tasksource/bigbench: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/bigbench/qwen3b_job7929_2026-04-04_07h15m35s',
            #     'tasksource/bigbench: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/bigbench/qwen3b_job1760_2026-04-10_15h44m06s',
            #     'tasksource/bigbench: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/bigbench/qwen3b_job1757_2026-04-10_15h29m23s',
            #     # 'tasksource/bigbench: No Mal Agent - answer': 'transcripts/MAS/answer/qwen3b_2026-03-29_21h46m31s',
            #     # 'tasksource/bigbench: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/bigbench/qwen3b_job8618_2026-04-05_12h39m16s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)


            # --- Malicious prompt comparison for Llama ---
transcript_data = {
    'openai/gsm8k: No Mal Agent': 'transcripts/MAS/both/llama3b_2026-03-29_15h19m52s',
    'openai/gsm8k: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/gsm8k/llama3b_job2569_2026-04-11_14h37m10s',
    'openai/gsm8k: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/gsm8k/llama3b_job5414_2026-04-08_13h29m50s',
    'openai/gsm8k: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/gsm8k/llama3b_job5376_2026-04-08_13h27m42s',
    # 'openai/gsm8k: No Mal Agent - answer': 'transcripts/MAS/answer/llama3b_job9704_2026-03-30_21h57m33s',
    # 'openai/gsm8k: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/gsm8k/llama3b_job8078_2026-04-04_12h52m39s',
}
malicious_comparison(transcript_data, round_figure=False)

            # # --- Malicious prompt comparison for Olmo ---
            # transcript_data = {
            #     'openai/gsm8k: No Mal Agent': 'transcripts/MAS/both/olmo7b_2026-03-29_15h41m56s',
            #     'openai/gsm8k: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/gsm8k/olmo7b_job7914_2026-04-04_02h03m27s',
            #     'openai/gsm8k: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/gsm8k/olmo7b_job5418_2026-04-08_23h19m55s',
            #     'openai/gsm8k: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/gsm8k/olmo7b_job5378_2026-04-08_13h27m42s',
            # #     'openai/gsm8k: No Mal Agent - answer': 'transcripts/MAS/answer/olmo7b_job126_2026-03-31_19h41m31s',
            # #     'openai/gsm8k: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/gsm8k/olmo7b_job8080_2026-04-04_12h53m27s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)

            # # --- Malicious prompt comparison for Qwen ---
            # transcript_data = {
            #     'openai/gsm8k: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
            #     'openai/gsm8k: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/gsm8k/qwen3b_job7913_2026-04-04_02h04m02s',
            #     'openai/gsm8k: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/gsm8k/qwen3b_job5417_2026-04-08_18h19m29s',
            #     'openai/gsm8k: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/gsm8k/qwen3b_job5377_2026-04-08_13h27m42s',
            #     # 'openai/gsm8k: No Mal Agent - answer': 'transcripts/MAS/answer/qwen3b_job9705_2026-03-30_21h58m14s',
            #     # 'openai/gsm8k: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/gsm8k/qwen3b_job8079_2026-04-04_12h53m27s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)


            # # --- Malicious prompt comparison for Llama ---
            # transcript_data = {
            #     'cais/mmlu: No Mal Agent': 'transcripts/MAS/both/llama3b_2026-03-29_00h34m49s',
            #     'cais/mmlu: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/mmlu/llama3b_job7915_2026-04-04_02h03m27s',
            #     'cais/mmlu: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/mmlu/llama3b_job5415_2026-04-08_13h29m51s',
            #     'cais/mmlu: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/mmlu/llama3b_job5383_2026-04-08_13h27m42s',
            #     # 'cais/mmlu: No Mal Agent - answer': 'transcripts/MAS/answer/llama3b_job349_2026-04-01_04h00m41s',
            #     # 'cais/mmlu: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/mmlu/llama3b_job8624_2026-04-05_12h38m21s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)

            # # --- Malicious prompt comparison for Olmo ---
            # transcript_data = {
            #     'cais/mmlu: No Mal Agent': 'transcripts/MAS/both/olmo7b_2026-03-29_15h29m53s',
            #     'cais/mmlu: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/mmlu/olmo7b_job7917_2026-04-04_02h03m27s',
            #     'cais/mmlu: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/mmlu/olmo7b_job5419_2026-04-09_06h17m09s',
            #     'cais/mmlu: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/mmlu/olmo7b_job5385_2026-04-08_13h27m42s',
            #     # 'cais/mmlu: No Mal Agent - answer': 'transcripts/MAS/answer/olmo7b_job124_2026-03-31_19h08m18s',
            #     # 'cais/mmlu: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/mmlu/olmo7b_job8626_2026-04-05_12h38m21s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)

            # # --- Malicious prompt comparison for Qwen ---
            # transcript_data = {
            #     'cais/mmlu: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h34m56s',
            #     'cais/mmlu: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/mmlu/qwen3b_job7916_2026-04-04_02h03m27s',
            #     'cais/mmlu: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/mmlu/qwen3b_job5416_2026-04-08_13h29m51s',
            #     'cais/mmlu: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/mmlu/qwen3b_job5384_2026-04-08_13h27m42s',
            #     # 'cais/mmlu: No Mal Agent - answer': 'transcripts/MAS/answer/qwen3b_job9914_2026-03-31_11h56m37s',
            #     # 'cais/mmlu: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/mmlu/qwen3b_job8625_2026-04-05_12h38m21s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)


            # # --- Malicious prompt comparison for Llama ---
            # transcript_data = {
            #     'ChilleD/StrategyQA: No Mal Agent': 'transcripts/MAS/both/llama3b_2026-03-29_15h21m49s',
            #     'ChilleD/StrategyQA: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/strategyQA/llama3b_job7919_2026-04-04_02h08m17s',
            #     'ChilleD/StrategyQA: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/strategyQA/llama3b_job5420_2026-04-09_06h36m40s',
            #     'ChilleD/StrategyQA: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/strategyQA/llama3b_job5386_2026-04-08_13h27m42s',
            #     # 'ChilleD/StrategyQA: No Mal Agent - answer': 'transcripts/MAS/answer/llama3b_job351_2026-04-01_07h39m19s',
            #     # 'ChilleD/StrategyQA: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/strategyQA/llama3b_job8620_2026-04-05_12h39m16s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)

            # # --- Malicious prompt comparison for Olmo ---
            # transcript_data = {
            #     'ChilleD/StrategyQA: No Mal Agent': 'transcripts/MAS/both/olmo7b_2026-03-29_15h26m25s',
            #     'ChilleD/StrategyQA: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/strategyQA/olmo7b_job7921_2026-04-04_02h09m58s',
            #     'ChilleD/StrategyQA: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/strategyQA/olmo7b_job5422_2026-04-09_09h45m17s',
            #     'ChilleD/StrategyQA: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/strategyQA/olmo7b_job5388_2026-04-09_15h24m11s',
            #     # 'ChilleD/StrategyQA: No Mal Agent - answer': 'transcripts/MAS/answer/olmo7b_job9973_2026-03-31_18h08m36s',
            #     # 'ChilleD/StrategyQA: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/strategyQA/olmo7b_job8622_2026-04-05_12h38m00s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)

            # # --- Malicious prompt comparison for Qwen ---
            # transcript_data = {
            #     'ChilleD/StrategyQA: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h26m25s',
            #     'ChilleD/StrategyQA: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/strategyQA/qwen3b_job7920_2026-04-04_02h08m17s',
            #     'ChilleD/StrategyQA: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/strategyQA/qwen3b_job5421_2026-04-09_08h09m11s',
            #     'ChilleD/StrategyQA: Mal Agent 2 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents2_3/strategyQA/qwen3b_job5387_2026-04-09_14h42m27s',
            #     # 'ChilleD/StrategyQA: No Mal Agent - answer': 'transcripts/MAS/answer/qwen3b_job9918_2026-03-31_17h05m39s',
            #     # 'ChilleD/StrategyQA: Mal Agent 1 & 2 - answer': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/strategyQA/qwen3b_job8621_2026-04-05_12h38m00s',
            # }
            # malicious_comparison(transcript_data, round_figure=False)

# ╔═════════════════════════════════════════════════╗
# ║                       RQ1                       ║
# ╚═════════════════════════════════════════════════╝

# # --- Comparison for openai/gsm8k, both, MAS ---
# transcript_data = {
#     'Qwen/Qwen2.5-3B-Instruct': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
#     'allenai/Olmo-3-7B-Instruct': 'transcripts/MAS/both/olmo7b_2026-03-29_15h41m56s',
#     'meta-llama/Llama-3.2-3B-Instruct': 'transcripts/MAS/both/llama3b_2026-03-29_15h19m52s',
# }
# dataset_comparison(transcript_data, round_figure=False, comparison_type='model')


# --- Comparison for cais/mmlu, both, MAS ---
# transcript_data = {
#     'Qwen/Qwen2.5-3B-Instruct': 'transcripts/MAS/both/...',
#     'allenai/Olmo-3-7B-Instruct': 'transcripts/MAS/both/...',
#     'meta-llama/Llama-3.2-3B-Instruct': 'transcripts/MAS/both/...',
# }
# dataset_comparison(transcript_data, round_figure=False, comparison_type='model')

# --- Comparison for ChilleD/StrategyQA, both, MAS ---
# transcript_data = {
#     'Qwen/Qwen2.5-3B-Instruct': 'transcripts/MAS/both/...',
#     'allenai/Olmo-3-7B-Instruct': 'transcripts/MAS/both/...',
#     'meta-llama/Llama-3.2-3B-Instruct': 'transcripts/MAS/both/...',
# }
# dataset_comparison(transcript_data, round_figure=False, comparison_type='model')


# --- Comparison for tasksource/bigbench, both, MAS ---
# transcript_data = {
#     'Qwen/Qwen2.5-3B-Instruct': 'transcripts/MAS/both/...',
#     'allenai/Olmo-3-7B-Instruct': 'transcripts/MAS/both/...',
#     'meta-llama/Llama-3.2-3B-Instruct': 'transcripts/MAS/both/...',
# }
# dataset_comparison(transcript_data, round_figure=False, comparison_type='tasksource/bigbench')


# ╔═════════════════════════════════════════════════╗
# ║                       RQ2                       ║
# ╚═════════════════════════════════════════════════╝

# ------ Comparison for QWEN, both, MAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
#     'cais/mmlu': 'transcripts/MAS/both/qwen3b_2026-03-29_15h34m56s',
#     'ChilleD/StrategyQA': 'transcripts/MAS/both/qwen3b_2026-03-29_15h26m25s',
#     'tasksource/bigbench': 'transcripts/MAS/both/qwen3b_2026-03-29_03h35m18s'
# }
# dataset_comparison(transcript_data, round_figure=True)

# # ------ Comparison for Olmo, both, MAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/MAS/both/olmo7b_2026-03-29_15h41m56s',
#     'cais/mmlu': 'transcripts/MAS/both/olmo7b_2026-03-29_15h29m53s',
#     'ChilleD/StrategyQA': 'transcripts/MAS/both/olmo7b_2026-03-29_15h26m25s',
#     'tasksource/bigbench': 'transcripts/MAS/both/olmo7b_2026-03-29_01h47m46s'
# }
# dataset_comparison(transcript_data, round_figure=True)

# # ------ Comparison for Llama, both, MAS --------
# transcript_data = {
#     'openai/gsm8k': 'transcripts/MAS/both/llama3b_2026-03-29_15h19m52s',
#     'cais/mmlu': 'transcripts/MAS/both/llama3b_2026-03-29_00h34m49s',
#     'ChilleD/StrategyQA': 'transcripts/MAS/both/llama3b_2026-03-29_15h21m49s',
#     'tasksource/bigbench': 'transcripts/MAS/both/llama3b_2026-03-29_03h08m47s'
# }
# dataset_comparison(transcript_data, round_figure=True)


# ╔═════════════════════════════════════════════════╗
# ║                       RQ3                       ║
# ╚═════════════════════════════════════════════════╝

# --- Malicious prompt comparison for Qwen ---
# transcript_data = {
#     'openai/gsm8k: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
#     'openai/gsm8k: Mal Agent 1 - Both': 'transcripts/MAS/malicious/gsm8k/qwen3b_job345_2026-04-01_01h35m32s',
#     'openai/gsm8k: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/gsm8k/qwen3b_job3963_2026-04-02_02h14m14s',
#     'cais/mmlu: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h34m56s',
#     'cais/mmlu: Mal Agent 1 - Both': 'transcripts/MAS/malicious/mmlu/qwen3b_job4470_2026-04-02_08h10m34s',
#     'cais/mmlu: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/mmlu/qwen3b_job7400_2026-04-03_01h36m45s',
#     'ChilleD/StrategyQA: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Mal Agent 1 - Both': 'transcripts/MAS/malicious/strategyQA/qwen3b_job7394_2026-04-03_01h31m22s',
#     'ChilleD/StrategyQA: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/strategyQA/qwen3b_job7387_2026-04-03_01h15m56s',
#     'tasksource/bigbench: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_03h35m18s',
#     'tasksource/bigbench: Mal Agent 1 - Both': 'transcripts/MAS/malicious/bigbench/qwen3b_job9921_2026-03-31_13h53m46s',
#     'tasksource/bigbench: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/bigbench/qwen3b_job9929_2026-03-31_16h56m02s',
# }
# malicious_comparison(transcript_data, round_figure=False, comparison_type='sharemode_malicious')

# # --- Malicious prompt comparison for Olmo ---
# transcript_data = {
#     'openai/gsm8k: No Mal Agent': 'transcripts/MAS/both/...,
#     'openai/gsm8k: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/gsm8k/...',
#     'openai/gsm8k: Mal Agent 1 - Both': 'transcripts/MAS/malicious/gsm8k/...',
#     'cais/mmlu: No Mal Agent': 'transcripts/MAS/both/...',
#     'cais/mmlu: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/mmlu/...',
#     'cais/mmlu: Mal Agent 1 - Both': 'transcripts/MAS/malicious/mmlu/...',
#     'ChilleD/StrategyQA: No Mal Agent': 'transcripts/MAS/both/...',
#     'ChilleD/StrategyQA: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/strategyQA/...',
#     'ChilleD/StrategyQA: Mal Agent 1 - Both': 'transcripts/MAS/malicious/strategyQA/...',
#     'tasksource/bigbench: No Mal Agent': 'transcripts/MAS/both/...',
#     'tasksource/bigbench: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/bigbench/...',
#     'tasksource/bigbench: Mal Agent 1 - Both': 'transcripts/MAS/malicious/bigbench/...',
# }
# malicious_comparison(transcript_data, round_figure=False, comparison_type='sharemode_malicious')

# # --- Malicious prompt comparison for Llama ---
# transcript_data = {
#     'openai/gsm8k: No Mal Agent': 'transcripts/MAS/both/...,
#     'openai/gsm8k: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/gsm8k/...',
#     'openai/gsm8k: Mal Agent 1 - Both': 'transcripts/MAS/malicious/gsm8k/...',
#     'cais/mmlu: No Mal Agent': 'transcripts/MAS/both/...',
#     'cais/mmlu: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/mmlu/...',
#     'cais/mmlu: Mal Agent 1 - Both': 'transcripts/MAS/malicious/mmlu/...',
#     'ChilleD/StrategyQA: No Mal Agent': 'transcripts/MAS/both/...',
#     'ChilleD/StrategyQA: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/strategyQA/...',
#     'ChilleD/StrategyQA: Mal Agent 1 - Both': 'transcripts/MAS/malicious/strategyQA/...',
#     'tasksource/bigbench: No Mal Agent': 'transcripts/MAS/both/...',
#     'tasksource/bigbench: Mal Agent 1 - Answer': 'transcripts/MAS/malicious/bigbench/...',
#     'tasksource/bigbench: Mal Agent 1 - Both': 'transcripts/MAS/malicious/bigbench/...',
# }
# malicious_comparison(transcript_data, round_figure=False, comparison_type='sharemode_malicious')



# ╔═════════════════════════════════════════════════╗
# ║                       RQ4                       ║
# ╚═════════════════════════════════════════════════╝

# # --- Comparison for QWEN, dataset, both ---
# transcript_data = {
#     'SAS': 'transcripts/MAS/both/...',
#     'MAS': 'transcripts/MAS/both/...',
# }
# dataset_comparison(transcript_data, round_figure=False, comparison_type='system')

# # --- Comparison for Olmo, dataset, both ---
# transcript_data = {
#     'SAS': 'transcripts/MAS/both/...',
#     'MAS': 'transcripts/MAS/both/...',
# }
# dataset_comparison(transcript_data, round_figure=False, comparison_type='system')

# --- Comparison for Llama, tasksource/bigbench, both ---
# transcript_data = {
#     'SAS': 'transcripts/SAS/both/llama3b_job9791_2026-03-31_09h16m39s',
#     'MAS': 'transcripts/MAS/both/llama3b_2026-03-29_03h08m47s',
# }
# dataset_comparison(transcript_data, round_figure=False, comparison_type='system')


# ╔═════════════════════════════════════════════════╗
# ║                       RQ5                       ║
# ╚═════════════════════════════════════════════════╝

# # --- Malicious prompt comparison for Qwen, both ---
# transcript_data = {
#     'openai/gsm8k: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
#     'openai/gsm8k: Mal Agent 1': 'transcripts/MAS/malicious/gsm8k/qwen3b_job345_2026-04-01_01h35m32s',
#     'openai/gsm8k: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/gsm8k/qwen3b_job7913_2026-04-04_02h04m02s',
#     'cais/mmlu: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h34m56s',
#     'cais/mmlu: Mal Agent 1': 'transcripts/MAS/malicious/mmlu/qwen3b_job4470_2026-04-02_08h10m34s',
#     'cais/mmlu: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/mmlu/qwen3b_job7916_2026-04-04_02h03m27s',
#     'ChilleD/StrategyQA: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Mal Agent 1': 'transcripts/MAS/malicious/strategyQA/qwen3b_job7394_2026-04-03_01h31m22s',
#     'ChilleD/StrategyQA: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/strategyQA/qwen3b_job7920_2026-04-04_02h08m17s',
#     'tasksource/bigbench: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_03h35m18s',
#     'tasksource/bigbench: Mal Agent 1': 'transcripts/MAS/malicious/bigbench/qwen3b_job9921_2026-03-31_13h53m46s',
#     'tasksource/bigbench: Mal Agent 1 & 2': 'transcripts/MAS/malicious/2maliciousAgents/agents1_2/bigbench/qwen3b_job7929_2026-04-04_07h15m35s',
# }
# malicious_comparison(transcript_data, round_figure=False, comparison_type='malicious_convergence')

# # --- Malicious prompt comparison for Qwen, both, 1 & 3 ---
# transcript_data = {
#     'openai/gsm8k: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
#     'openai/gsm8k: Mal Agent 1': 'transcripts/MAS/malicious/gsm8k/qwen3b_job345_2026-04-01_01h35m32s',
#     'openai/gsm8k: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/gsm8k/qwen3b_job5417_2026-04-08_18h19m29s',
#     'cais/mmlu: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h34m56s',
#     'cais/mmlu: Mal Agent 1': 'transcripts/MAS/malicious/mmlu/qwen3b_job4470_2026-04-02_08h10m34s',
#     'cais/mmlu: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/mmlu/qwen3b_job5416_2026-04-08_13h29m51s',
#     'ChilleD/StrategyQA: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Mal Agent 1': 'transcripts/MAS/malicious/strategyQA/qwen3b_job7394_2026-04-03_01h31m22s',
#     'ChilleD/StrategyQA: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/strategyQA/qwen3b_job5421_2026-04-09_08h09m11s',
#     'tasksource/bigbench: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_03h35m18s',
#     'tasksource/bigbench: Mal Agent 1': 'transcripts/MAS/malicious/bigbench/qwen3b_job9921_2026-03-31_13h53m46s',
#     'tasksource/bigbench: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/bigbench/qwen3b_job1760_2026-04-10_15h44m06s',
# }
# malicious_comparison(transcript_data, round_figure=False, comparison_type='malicious_convergence')

# --- Malicious prompt comparison for Llama, both ---
# transcript_data = {
#     'openai/gsm8k: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_00h31m15s',
#     'openai/gsm8k: Mal Agent 1': 'transcripts/MAS/malicious/gsm8k/qwen3b_job345_2026-04-01_01h35m32s',
#     'openai/gsm8k: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/gsm8k/qwen3b_job5417_2026-04-08_18h19m29s',
#     'cais/mmlu: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h34m56s',
#     'cais/mmlu: Mal Agent 1': 'transcripts/MAS/malicious/mmlu/qwen3b_job4470_2026-04-02_08h10m34s',
#     'cais/mmlu: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/mmlu/qwen3b_job5416_2026-04-08_13h29m51s',
#     'ChilleD/StrategyQA: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_15h26m25s',
#     'ChilleD/StrategyQA: Mal Agent 1': 'transcripts/MAS/malicious/strategyQA/qwen3b_job7394_2026-04-03_01h31m22s',
#     'ChilleD/StrategyQA: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/strategyQA/qwen3b_job5421_2026-04-09_08h09m11s',
#     'tasksource/bigbench: No Mal Agent': 'transcripts/MAS/both/qwen3b_2026-03-29_03h35m18s',
#     'tasksource/bigbench: Mal Agent 1': 'transcripts/MAS/malicious/bigbench/qwen3b_job9921_2026-03-31_13h53m46s',
#     'tasksource/bigbench: Mal Agent 1 & 3': 'transcripts/MAS/malicious/2maliciousAgents/agents1_3/bigbench/qwen3b_job1760_2026-04-10_15h44m06s',
# }
# malicious_comparison(transcript_data, round_figure=False, comparison_type='malicious_convergence')


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
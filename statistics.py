import re
import matplotlib.pyplot as plt

def extract_answers(file_path, num_tasks, num_agents):
    answer_regex = r"(?<=answered: )(\w+)"
    correct_answer_regex = r"(?<=Correct Answer: )(\w+)"

    tasks = dict()

    for i in range(1, num_tasks + 1):
        # Read the entire file as a string
        with open(file_path + '/task' + str(i) + '.txt', 'r') as file:
            text = file.read()

        result = re.findall(answer_regex, text)
        init_answer = result[0:num_agents]
        final_answer = result[num_agents:]
        correct_answer = re.findall(correct_answer_regex, text)

        tasks[i] = (init_answer, final_answer, correct_answer)
        
    return tasks

tasks_answers = extract_answers('/home/xng137/SPECIALE/HiddenBench_newest/transcripts/2026-03-08_17h59m42s', 15, 3)

# print(tasks_answers)
# print(tasks_answers[1][0])
# print(tasks_answers[1][1])
# print(tasks_answers[1][2])

def statistics(tasks_answers):
    wrong_correct = 0
    wrong_different_wrong = 0
    correct_correct = 0
    wrong_same_wrong = 0
    total_count = 0
    missed_patterns = 0
    missed_patterns_dict = dict()

    for task_num, (init_answer, final_answer, correct_answer) in tasks_answers.items():
        print(f"Task {task_num}:")
        print(f"  Initial Answers: {init_answer}")
        print(f"  Final Answers: {final_answer}")
        print(f"  Correct Answer: {correct_answer}")

        wrong_init_answer = all(answer != correct_answer[0] for answer in init_answer)
        correct_final_answer = all(answer == correct_answer[0] for answer in final_answer)
        

        if wrong_init_answer and correct_final_answer:
            print("Wrong answer in the beginning, but converges to the correct answer")
            wrong_correct += 1
            total_count += 1
        elif wrong_init_answer and not correct_final_answer and init_answer != final_answer:
            print("Wrong answer in the beginning, but converges to a different wrong answer")
            wrong_different_wrong += 1
            total_count += 1
        elif not wrong_init_answer and correct_final_answer:
            print("Correct answer in the beginning and end")
            correct_correct += 1
            total_count += 1
        elif wrong_init_answer and init_answer == final_answer:
            print("Same wrong answer in the beginning and end")
            wrong_same_wrong += 1
            total_count += 1
        else:
            missed_patterns += 1
            missed_patterns_dict[task_num] = (init_answer, final_answer, correct_answer)

    print(missed_patterns, "tasks did not fit any of the defined patterns.")
    # Create a bar chart
    categories = ['Wrong→Correct', 'Wrong→Different Wrong', 'Correct→Correct', 'Wrong→Same Wrong']
    counts = [wrong_correct, wrong_different_wrong, correct_correct, wrong_same_wrong]
    percentages = [(count / total_count) * 100 for count in counts]
    
    
    #plt.figure(figsize=(12, 6))  # Make the figure wider: 12 inches wide, 6 inches tall
    plt.bar(categories, percentages)
    plt.ylabel('Percentage (%) of Tasks')
    plt.xlabel('Answer Pattern')
    plt.title('Task Answer Statistics')
    plt.xticks(rotation=45, ha='right')  # Rotate labels 45 degrees
    plt.tight_layout()  # Adjust spacing so labels don't get cut off
    plt.savefig('statistics.png')
    print("Plot saved as statistics.png")



# TODO Correct reasoning in the beginning, but wrong answer

statistics(tasks_answers)


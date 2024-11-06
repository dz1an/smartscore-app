import random

def generate_unique_sets_by_category(question_pool, num_sets, num_easy, num_medium, num_hard):
    # Calculate the total number of questions per set
    total_questions_per_set = num_easy + num_medium + num_hard

    # Separate the questions by difficulty categories
    easy_questions = [q for q in question_pool if q['difficulty'] == 'easy']
    medium_questions = [q for q in question_pool if q['difficulty'] == 'medium']
    hard_questions = [q for q in question_pool if q['difficulty'] == 'hard']
    
    # Error handling: Ensure there are enough questions in each category
    if len(easy_questions) < num_easy:
        raise ValueError(f"Not enough easy questions! You need {num_easy} easy questions per set, but only {len(easy_questions)} are available.")
    
    if len(medium_questions) < num_medium:
        raise ValueError(f"Not enough medium questions! You need {num_medium} medium questions per set, but only {len(medium_questions)} are available.")
    
    if len(hard_questions) < num_hard:
        raise ValueError(f"Not enough hard questions! You need {num_hard} hard questions per set, but only {len(hard_questions)} are available.")
    
    # Create a list to store unique sets
    unique_sets = []
    
    for _ in range(num_sets):
        # Randomly select questions from each difficulty category
        easy_set = random.sample(easy_questions, num_easy)
        medium_set = random.sample(medium_questions, num_medium)
        hard_set = random.sample(hard_questions, num_hard)
        
        # Combine the selected questions into a single set
        exam_set = easy_set + medium_set + hard_set
        
        # Check if the total number of questions per set is correct
        if len(exam_set) != total_questions_per_set:
            raise ValueError(f"Set creation failed! Expected {total_questions_per_set} questions per set, but got {len(exam_set)}.")

        # Shuffle the set to mix up the difficulty levels
        random.shuffle(exam_set)
        
        # Add this set to the list of unique sets
        unique_sets.append(exam_set)
    
    return unique_sets

# Example usage
question_pool = [
    {'id': 1, 'difficulty': 'easy'}, 
    {'id': 2, 'difficulty': 'easy'},
    {'id': 3, 'difficulty': 'medium'}, 
    {'id': 4, 'difficulty': 'medium'},
    {'id': 5, 'difficulty': 'hard'}, 
    {'id': 6, 'difficulty': 'hard'},
    # Add more questions here...
]

num_sets = 5  # Number of unique sets you want to generate
num_easy = 2  # Number of easy questions per set
num_medium = 2  # Number of medium questions per set
num_hard = 2  # Number of hard questions per set

try:
    # Generate the unique sets
    unique_exam_sets = generate_unique_sets_by_category(question_pool, num_sets, num_easy, num_medium, num_hard)
    
    # Print out the sets
    for i, exam_set in enumerate(unique_exam_sets):
        print(f"Set {i + 1}: {exam_set}")
except ValueError as e:
    # Print the error message if any validation fails
    print(f"Error: {e}")

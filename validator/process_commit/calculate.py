def check_similarity(sample_similarities):
    """
    Check if the proportion of similarities less than or equal to 70
    exceeds a threshold of 30% of the total sample size.

    Parameters:
    sample_similarities (list of int): A list of similarity scores.

    Returns:
    int: 0 if the condition is met, otherwise 1.
    """
    threshold_count = 0.3 * len(sample_similarities)
    count = sum(1 for similarity in sample_similarities if similarity <= 70)

    if count >= threshold_count:
        return 0
    else:
        return 1

def calculate_data_quality(value, stderr):
    return value / (stderr + 1)

def calculate_score(time_elapsed, value, stderr, sample_similarities, x=0.5):
    """
    Calculate a score based on time elapsed, value, and sample similarities.
    """

    # Check if 70% of sample similarities are over 70
    if check_similarity(sample_similarities) == 0:
        return 0
    data_quality = calculate_data_quality(value, stderr)

    score = (time_elapsed * x) + (data_quality * (1 - x))
    
    return score
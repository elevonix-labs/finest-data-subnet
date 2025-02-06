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

    return 0 if count >= threshold_count else 1


def calculate_data_quality(value, stderr):
    return value * (1 - stderr)


def calculate_score(time_elapsed, value, stderr, sample_similarities, x=0.7):
    """
    Calculate a score based on time elapsed, value, and sample similarities.
    """

    # Verify if 70% of sample similarities exceed 70
    if check_similarity(sample_similarities) == 0:
        return 0

    data_quality = calculate_data_quality(value, stderr)

    print(f"Value: {value}")
    print(f"Stderr: {stderr}")
    print(f"Data quality: {data_quality}")
    print(f"Time elapsed: {time_elapsed}")

    T_MAX = 3600 * 24  # 1 day in seconds

    score = x * data_quality + (1 - x) * (1 - time_elapsed / T_MAX)

    return score

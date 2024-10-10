# SharedVariables.py

num_images = 0
current_image_num = 0
date_format = None
date_range = None
batches = {}

def reset():
    global num_images
    global current_image_num
    global date_format
    global date_range
    global batches

    num_images = 0
    current_image_num = 0
    date_format = None
    date_range = None
    batches = {}

# Add this function to get all variables as a dictionary
def get_all():
    return {
        'num_images': num_images,
        'current_image_num': current_image_num,
        'date_format': date_format,
        'date_range': date_range,
        'batches': batches
    }
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements file
COPY requirements_minimal.txt ${LAMBDA_TASK_ROOT}/

# Install dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements_minimal.txt

# Copy application code
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY data/tickers.csv ${LAMBDA_TASK_ROOT}/
COPY src/lambda_handler.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "lambda_handler.lambda_handler" ]

FROM public.ecr.aws/lambda/python:3.11

# Copy requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}/

# Upgrade pip to latest version for better wheel support
RUN pip install --upgrade pip

# Install build dependencies for packages that require compilation
# - gcc, gcc-c++: C/C++ compilers (for contourpy, matplotlib deps)
# - curl: Download rustup installer
RUN yum install -y gcc gcc-c++ curl && yum clean all

# Install Rust compiler (required for tiktoken)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install dependencies
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY src/ ${LAMBDA_TASK_ROOT}/src/
COPY data/ ${LAMBDA_TASK_ROOT}/data/
COPY db/ ${LAMBDA_TASK_ROOT}/db/

# Copy all handler files to root for Lambda function entry points
COPY src/lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY src/report_worker_handler.py ${LAMBDA_TASK_ROOT}/
COPY src/telegram_lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY src/migration_handler.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler
CMD [ "lambda_handler.lambda_handler" ]

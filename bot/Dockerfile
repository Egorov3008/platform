FROM python:3.11-slim                                                                                                                       
                                                                                                                                              
  WORKDIR /app                                                                                                                                
   
  # Системные зависимости для asyncpg                                                                                                         
  RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \                                                                                                                                   
      && rm -rf /var/lib/apt/lists/*
                                                                                                                                              
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt                                                                                          
                  
  COPY . .

  # Директории для логов                                                                                                                      
  RUN mkdir -p logs logs_error
                                                                                                                                              
  CMD ["python", "main.py"]
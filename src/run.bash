echo "🔨 Building Docker image..."
docker build -t soil-moisture-fetcher .

docker run --rm \
  -v C:/Users/youmt/.config/earthengine:/root/.config/earthengine \
  --env-file .env \
  soil-moisture-fetcher

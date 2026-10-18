FROM node:lts-alpine

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG BACKEND_INTERNAL_URL=http://backend:8000
ENV BACKEND_INTERNAL_URL=${BACKEND_INTERNAL_URL}
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]

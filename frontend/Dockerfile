FROM node:26

WORKDIR /app

COPY package*.json ./
RUN --mount=type=cache,target=/root/.npm npm install

COPY . .

EXPOSE 9000

CMD ["npm", "run", "dev"]
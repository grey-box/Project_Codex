FROM node:26

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 9000

CMD ["npm", "run", "dev"]
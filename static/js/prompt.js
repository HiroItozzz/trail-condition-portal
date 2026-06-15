const path = window.location.pathname;
const pk = path.split("/").at(-2);
const sourceData = await getDataSource(pk);
const promptData = await getPrompt(pk);
const templateData = await getTemplate();
console.log(pk);
console.log(sourceData);
console.log(promptData);
console.log(templateData);

const sourceName = document.getElementById("source-name");
const filename = document.getElementById("filename");
const prompt = document.getElementById("prompt");
const model = document.getElementById("model");
const temperature = document.getElementById("temperature");
const thinkingBudget = document.getElementById("thinking_budget");
const useTemplate = document.getElementById("use-template");

sourceName.textContent = sourceData.name;
filename.textContent = sourceData.prompt_filename;
prompt.value = promptData.prompt;
model.value = promptData.model;
temperature.value = promptData.temperature;
thinkingBudget.value = promptData.thinking_budget;
useTemplate.checked = true ? promptData.use_template : false;

async function getDataSource(pk) {
  const res = await fetch(`http://localhost:8000/api/source/${pk}/`);
  return await res.json();
}

async function getPrompt(pk) {
  const res = await fetch(`http://localhost:8000/api/prompt/${pk}/`);
  return await res.json();
}

async function getTemplate() {
  const res = await fetch("http://localhost:8000/api/prompt/");
  return await res.json();
}

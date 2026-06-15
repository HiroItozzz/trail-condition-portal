class PromptFile {
  constructor(prompt, model, temperature, thinking_budget, use_template = null) {
    this.prompt = prompt;
    this.model = model;
    this.temperature = temperature;
    this.thinkingBudget = thinking_budget;
    this.useTemplate = use_template;
  }
}

class PromptFile2 {
  constructor(data) {
    Object.assign(this, data);
  }
}

const path = window.location.pathname;
const pk = path.split("/").at(-2);
const sourceData = await getDataSource(pk);
const promptData = await getPrompt(pk);
const templateData = await getTemplate();
console.log(pk);
console.log(sourceData);
console.log(promptData);
console.log(templateData);

const pf2 = new PromptFile2(promptData);
console.log(pf2);

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
useTemplate.checked = promptData.use_template ? true : false;

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

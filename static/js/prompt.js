async function getDataSource(pk) {
  const res = await fetch(`http://localhost:8000/api/source/${pk}/`);
  return await res.json();
}

async function getSiteConfig(pk) {
  const res = await fetch(`http://localhost:8000/api/prompt/${pk}/`);
  return await res.json();
}

async function getTemplate() {
  const res = await fetch("http://localhost:8000/api/prompt/");
  return await res.json();
}

const path = window.location.pathname;
const pk = Number(document.body.dataset.sourceId);
const [sourceData, individualData, templateData] = await Promise.all([
  getDataSource(pk),
  getSiteConfig(pk),
  getTemplate(),
]);

const sourceName = document.getElementById("source-name");
const filenameDisplay = document.getElementById("filename-display");
const filename = document.getElementById("filename");

// 画面左側
const form = {
  promptNullCheck: document.getElementById("prompt-null-check"),
  prompt: document.getElementById("prompt"),
  modelNullCheck: document.getElementById("model-null-check"),
  model: document.getElementById("model"),
  tempNullCheck: document.getElementById("temp-null-check"),
  temperature: document.getElementById("temperature"),
  temperatureNumber: document.getElementById("temperature-number"),
  thinkNullCheck: document.getElementById("think-null-check"),
  thinkingBudget: document.getElementById("thinking-budget"),
  thinkingBudgetNumber: document.getElementById("thinking-budget-number"),
  useTemplate: document.getElementById("use-template"),
};

// 画面右側
const mergedOutput = {
  prompt: document.getElementById("merged-prompt"),
  model: document.getElementById("merged-model"),
  temperature: document.getElementById("merged-temperature"),
  temperatureNumber: document.getElementById("merged-temperature-number"),
  thinkingBudget: document.getElementById("merged-thinking-budget"),
  thinkingBudgetNumber: document.getElementById("merged-thinking-budget-number"),
};

const promptIsNull = individualData.prompt === null;
const modelIsNull = individualData.config.model === null;
const tempIsNull = individualData.config.temperature === null;
const thinkIsNull = individualData.config.thinkingBudget === null;

sourceName.textContent = sourceData.name;
filenameDisplay.textContent = sourceData.prompt_filename;
filename.value = sourceData.prompt_filename;

// Form初期値の反映
form.prompt.value = individualData.prompt;
form.model.value = individualData.config.model ?? templateData.config.model;
form.temperature.value = individualData.config.temperature ?? templateData.config.temperature;
form.temperatureNumber.value = individualData.config.temperature ?? templateData.config.temperature;
form.thinkingBudget.value = individualData.config.thinkingBudget ?? templateData.config.thinkingBudget;
form.thinkingBudgetNumber.value = individualData.config.thinkingBudget ?? templateData.config.thinkingBudget;
form.useTemplate.checked = individualData.config.useTemplate ?? true;
form.promptNullCheck.checked = promptIsNull;
form.modelNullCheck.checked = modelIsNull;
form.tempNullCheck.checked = tempIsNull;
form.thinkNullCheck.checked = thinkIsNull;

// disabledの適用
form.prompt.disabled = form.promptNullCheck.checked;
form.model.disabled = form.modelNullCheck.checked;
form.temperature.disabled = form.tempNullCheck.checked;
form.temperatureNumber.disabled = form.tempNullCheck.checked;
form.thinkingBudget.disabled = form.thinkNullCheck.checked;
form.thinkingBudgetNumber.disabled = form.thinkNullCheck.checked;

// テンプレートと個別プロンプトのマージ
async function mergePrompt() {
  if (form.promptNullCheck.checked) {
    mergedOutput.prompt.value = templateData.prompt;
  } else {
    mergedOutput.prompt.value = `${templateData.prompt}\n\n${form.prompt.value}`;
  }
}
async function mergeModel() {
  if (form.modelNullCheck.checked) {
    mergedOutput.model.value = templateData.config.model;
  } else {
    mergedOutput.model.value = form.model.value;
  }
}
async function mergeTemp() {
  if (form.tempNullCheck.checked) {
    mergedOutput.temperature.value = templateData.config.temperature;
    mergedOutput.temperatureNumber.value = templateData.config.temperature;
  } else {
    mergedOutput.temperature.value = form.temperature.value;
    mergedOutput.temperatureNumber.value = form.temperatureNumber.value;
  }
}
async function mergeThink() {
  if (form.thinkNullCheck.checked) {
    mergedOutput.thinkingBudget.value = templateData.config.thinkingBudget;
    mergedOutput.thinkingBudgetNumber.value = templateData.config.thinkingBudget;
  } else {
    mergedOutput.thinkingBudget.value = form.thinkingBudget.value;
    mergedOutput.thinkingBudgetNumber.value = form.thinkingBudgetNumber.value;
  }
}
const mergeTemplate = async () => {
  await Promise.all([mergePrompt(), mergeModel(), mergeTemp(), mergeThink()]);
};

// テンプレートの初期化
await mergeTemplate();

// テンプレートの適用の解除関数
async function disableTemplate(form) {
  mergedOutput.prompt.value = form.prompt.value;
  mergedOutput.model.value = form.model.value;
  mergedOutput.temperature.value = form.temperature.value;
  mergedOutput.temperatureNumber.value = form.temperatureNumber.value;
  mergedOutput.thinkingBudget.value = form.thinkingBudget.value;
  mergedOutput.thinkingBudgetNumber.value = form.thinkingBudgetNumber.value;
}

// useTemplateのオンオフの適用
form.useTemplate.addEventListener("change", async (event) => {
  if (form.useTemplate.checked) {
    await mergeTemplate();
  } else {
    await disableTemplate(form);
  }
});

// チェックボックスとdisabled、出力プロンプトの連携
form.promptNullCheck.addEventListener("change", async (event) => {
  form.prompt.disabled = form.promptNullCheck.checked;
  await mergePrompt();
});
form.modelNullCheck.addEventListener("change", async (event) => {
  form.model.disabled = form.modelNullCheck.checked;
  await mergeModel();
});
form.tempNullCheck.addEventListener("change", async (event) => {
  form.temperature.disabled = form.tempNullCheck.checked;
  form.temperatureNumber.disabled = form.tempNullCheck.checked;
  await mergeTemp();
});
form.thinkNullCheck.addEventListener("change", async (event) => {
  form.thinkingBudget.disabled = form.thinkNullCheck.checked;
  form.thinkingBudgetNumber.disabled = form.thinkNullCheck.checked;
  await mergeThink();
});
form.prompt.addEventListener("input", async (event) => {
  await mergePrompt();
});
form.model.addEventListener("input", async (event) => {
  await mergeModel();
});
form.temperature.addEventListener("input", async (event) => {
  form.temperatureNumber.value = form.temperature.value;
  await mergeTemp();
});
form.thinkingBudget.addEventListener("input", async (event) => {
  form.thinkingBudgetNumber.value = form.thinkingBudget.value;
  await mergeThink();
});

// 数字とつまみの連携
form.temperatureNumber.addEventListener("change", (event) => {
  form.temperature.value = form.temperatureNumber.value;
});
form.thinkingBudgetNumber.addEventListener("change", (event) => {
  form.thinkingBudget.value = form.thinkingBudgetNumber.value;
});
mergedOutput.temperature.addEventListener("change", (event) => {
  mergedOutput.temperatureNumber.value = mergedOutput.temperature.value;
});
mergedOutput.temperatureNumber.addEventListener("change", (event) => {
  mergedOutput.temperature.value = mergedOutput.temperatureNumber.value;
});
mergedOutput.thinkingBudget.addEventListener("change", (event) => {
  mergedOutput.thinkingBudgetNumber.value = mergedOutput.thinkingBudget.value;
});
mergedOutput.thinkingBudgetNumber.addEventListener("change", (event) => {
  mergedOutput.thinkingBudget.value = mergedOutput.thinkingBudgetNumber.value;
});

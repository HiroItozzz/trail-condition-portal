async function getSourceList() {
    const res = await fetch(`/api/source/list/`);
    return await res.json();
}

async function getSiteConfig(sourceId) {
    const res = await fetch(`/api/prompt/${sourceId}/`);
    const data = await res.json()
    return data;
}

async function getTemplate() {
    const res = await fetch("/api/prompt/");
    return await res.json();
}

export const sourceId = Number(document.body.dataset.sourceId);
const [sourceList, individualData, templateData] = await Promise.all([
    getSourceList(),
    getSiteConfig(sourceId),
    getTemplate(),
]);

const sourceName = document.getElementById("source-name");
const filenameDisplay = document.getElementById("filename-display");
const filename = document.getElementById("filename");

// ヘッダーのドロップダウン
const sourceSelect = document.getElementById("source-select")
const createSrcOption = ({pk, name}) => {
    const option = document.createElement("option");
    option.value = pk;
    option.textContent = name;
    option.selected = pk === sourceId;
    sourceSelect.appendChild(option);
}
sourceList.forEach(createSrcOption);

// 情報源セレクトボックスのイベントリスナー
sourceSelect.addEventListener("change", (ev) => {
    const pk = ev.target.value
    location.href = `/prompt/${pk}/`;
})

// 画面左側フォーム
export const form = document.querySelector("form")

// 画面右側出力結果
const merged = {
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

const initCheckbox = () => {
    form.promptNullCheck.checked = promptIsNull;
    form.modelNullCheck.checked = modelIsNull;
    form.tempNullCheck.checked = tempIsNull;
    form.thinkNullCheck.checked = thinkIsNull;
    // disabledの初期化
    form.prompt.disabled = promptIsNull;
    form.model.disabled = modelIsNull;
    form.temperature.disabled = tempIsNull;
    form.temperatureNumber.disabled = tempIsNull;
    form.thinkingBudget.disabled = thinkIsNull;
    form.thinkingBudgetNumber.disabled = thinkIsNull;
}
// Form初期化関数
const initForm = () => {
    filename.value = individualData.filename;
    form.prompt.value = individualData.prompt;
    form.model.value = individualData.config.model ?? templateData.config.model;
    form.temperature.value = individualData.config.temperature ?? templateData.config.temperature;
    form.temperatureNumber.value = individualData.config.temperature ?? templateData.config.temperature;
    form.thinkingBudget.value = individualData.config.thinkingBudget ?? templateData.config.thinkingBudget;
    form.thinkingBudgetNumber.value = individualData.config.thinkingBudget ?? templateData.config.thinkingBudget;
    form.useTemplate.checked = individualData.config.useTemplate ?? true;
    initCheckbox()
}
// テンプレートと個別プロンプトのマージ関数
const mergePrompt = () => {
    const box = [];
    if (form.useTemplate.checked) {
        box.push(templateData.prompt);
    }
    if (!form.promptNullCheck.checked) {
        box.push(form.prompt.value);
    }
    merged.prompt.value = box.join("\n\n")
}
const mergeModel = () => {
    if (form.modelNullCheck.checked) {
        merged.model.value = templateData.config.model;
    } else {
        merged.model.value = form.model.value;
    }
}
const mergeTemp = () => {
    if (form.tempNullCheck.checked) {
        merged.temperature.value = templateData.config.temperature;
        merged.temperatureNumber.value = templateData.config.temperature;
    } else {
        merged.temperature.value = form.temperature.value;
        merged.temperatureNumber.value = form.temperatureNumber.value;
    }
}
const mergeThink = () => {
    if (form.thinkNullCheck.checked) {
        merged.thinkingBudget.value = templateData.config.thinkingBudget;
        merged.thinkingBudgetNumber.value = templateData.config.thinkingBudget;
    } else {
        merged.thinkingBudget.value = form.thinkingBudget.value;
        merged.thinkingBudgetNumber.value = form.thinkingBudgetNumber.value;
    }
}
const mergeTemplate = () => {
    mergePrompt();
    mergeModel();
    mergeTemp();
    mergeThink();
};

const inputFields = [
    {name: "prompt", nullCheck: form.promptNullCheck, formEl: [form.prompt], mergeMethod: mergePrompt},
    {name: "model", nullCheck: form.modelNullCheck, formEl: [form.model], mergeMethod: mergeModel},
    {
        name: "temperature",
        nullCheck: form.tempNullCheck,
        formEl: [form.temperature, form.temperatureNumber],
        mergeMethod: mergeTemp
    },
    {
        name: "thinkingBudget",
        nullCheck: form.thinkNullCheck,
        formEl: [form.thinkingBudget, form.thinkingBudgetNumber],
        mergeMethod: mergeThink
    }
]

// テンプレートの適用の解除関数
const disableTemplate = () => {
    merged.prompt.value = form.prompt.value;
    merged.model.value = form.model.value;
    merged.temperature.value = form.temperature.value;
    merged.temperatureNumber.value = form.temperatureNumber.value;
    merged.thinkingBudget.value = form.thinkingBudget.value;
    merged.thinkingBudgetNumber.value = form.thinkingBudgetNumber.value;
}

// useTemplateのオンオフの適用
form.useTemplate.addEventListener("change", (event) => {
    if (form.useTemplate.checked) {
        initCheckbox()
        mergeTemplate();

    } else {
        inputFields.forEach(({nullCheck}) => nullCheck.checked = false)
        inputFields.forEach(({formEl}) => formEl.forEach((el) => el.disabled = false))
        disableTemplate();
    }
});

// 数字とつまみの連携
const syncPair = (rangeEl, numberEl) => {
    rangeEl.addEventListener("input", () => {
        numberEl.value = rangeEl.value;
    });
    numberEl.addEventListener("input", () => {
        rangeEl.value = numberEl.value
    })
}
syncPair(form.temperature, form.temperatureNumber);
syncPair(form.thinkingBudget, form.thinkingBudgetNumber);


// 画面左右の連携
const applyInput = ({nullCheck, formEl, mergeMethod}) => {
    // テンプレート不使用チェックボックスを右側出力へ反映
    nullCheck.addEventListener("change", () => {
        formEl.forEach((el) => el.disabled = nullCheck.checked);
        mergeMethod()
    });
    // 各フォーム入力を右側出力へ反映
    formEl.forEach((el) => el.addEventListener("input", () => mergeMethod()
    ));
}

// ユーザー入力のイベントリスナー
inputFields.forEach(applyInput);
form.resetBtn.addEventListener("click", () => {
    if (window.confirm("プロンプトを初期状態に戻しますか？")) {
        initForm();
        form.useTemplate.checked ? mergeTemplate() : disableTemplate();
    }
})

form.promptNullCheck.addEventListener("change", (ev) => {
    if (!ev.target.checked) {
        merged.prompt.scrollTop = merged.prompt.scrollHeight;
    }
})

form.prompt.addEventListener("input", (ev) => {
    merged.prompt.scrollTop = merged.prompt.scrollHeight;
})

window.addEventListener('beforeunload', (event) => {
    // 警告メッセージを表示する（ブラウザによっては標準の文言になります）
    event.preventDefault();
    event.returnValue = ''; // 標準ダイアログ用
});

// 情報源とファイル名（固定値）
sourceName.textContent = sourceList.find(({pk}) => pk === sourceId)?.name ?? "";
filenameDisplay.textContent = individualData.filename;

// form初期化
initForm();
// テンプレートの初期化
form.useTemplate.checked ? mergeTemplate() : disableTemplate();

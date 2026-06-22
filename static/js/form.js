import {form, pk} from "./prompt.js";

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

async function sendData() {
    // FormData オブジェクトをフォーム要素に関連付ける
    const formData = new FormData(form);

    try {
        const response = await fetch(`http://localhost:8000/api/prompt/${pk}/post/`, {
            method: "POST",
            // FormData インスタンスをリクエスト本体として設定
            body: formData,
            headers: {
                'X-CSRFToken': csrftoken
            }
        });
        console.log(await response.json());
    } catch (e) {
        console.error(e);
    }
}

form.addEventListener('submit', async (ev) => {
    ev.preventDefault();
    if (window.confirm("現在のプロンプトの変更を反映しますか？")) {
        await sendData()
    }
});

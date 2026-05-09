const API_URL = "";let currentLang = "ar";
let lastBuilds = [];
let currentCurrency = "OMR";

const CURRENCY_RATES = {
    USD: 1,
    OMR: 0.385,
    EUR: 0.92,
    SAR: 3.75,
};

const CURRENCY_LABELS = {
    ar: {
        OMR: "ريال عماني",
        USD: "دولار",
        EUR: "يورو",
        SAR: "ريال سعودي",
    },
    en: {
        OMR: "OMR",
        USD: "USD",
        EUR: "EUR",
        SAR: "SAR",
    },
};

function setLang(lang) {
    currentLang = lang;
    const html = document.documentElement;

    html.setAttribute("lang", lang);
    html.setAttribute("dir", lang === "ar" ? "rtl" : "ltr");

    document.querySelectorAll("[data-ar]").forEach(el => {
        el.textContent = el.getAttribute(`data-${lang}`);
    });

    document.querySelectorAll("[data-placeholder-ar]").forEach(el => {
        el.placeholder = el.getAttribute(`data-placeholder-${lang}`);
    });

    document.querySelectorAll("option[data-ar]").forEach(el => {
        el.textContent = el.getAttribute(`data-${lang}`);
    });

    document.getElementById("btn-ar").classList.toggle("active", lang === "ar");
    document.getElementById("btn-en").classList.toggle("active", lang === "en");

    if (lastBuilds.length > 0 && !document.getElementById("result-section").classList.contains("hidden")) {
        showResults(lastBuilds);
    }
}

function onCurrencyChange() {
    currentCurrency = document.getElementById("currency").value;
    if (lastBuilds.length > 0 && !document.getElementById("result-section").classList.contains("hidden")) {
        showResults(lastBuilds);
    }
}

function convertPrice(priceUsd) {
    return Number(priceUsd || 0) * CURRENCY_RATES[currentCurrency];
}

function convertEnteredToUsd(enteredValue) {
    const rate = CURRENCY_RATES[currentCurrency] || 1;
    return Number(enteredValue || 0) / rate;
}

function formatPrice(priceUsd) {
    const converted = convertPrice(priceUsd);
    const rounded = Number(converted.toFixed(2));
    return `${rounded} ${CURRENCY_LABELS[currentLang][currentCurrency]}`;
}

const messages = {
    fillAll:      { ar: "يرجى تعبئة جميع الحقول: الميزانية، الغرض، الخوارزمية.", en: "Please fill in all fields: Budget, Purpose, and Algorithm." },
    minBudget:    { ar: "الحد الأدنى للميزانية هو $300.", en: "Minimum budget is $300." },
    noServer:     { ar: "تعذّر الاتصال بالسيرفر. تأكد من تشغيل Flask على المنفذ 5000.", en: "Cannot connect to server. Make sure Flask is running on port 5000." },
    noBuild:      { ar: "لم يُوجد بناء صالح ضمن ميزانيتك.", en: "No valid build found within your budget." },
    searching:    { ar: "جارٍ البحث عن أفضل بناء...", en: "Searching for the best build..." },
    compatible:   { ar: "جميع المكونات متوافقة ✅", en: "All components are compatible ✅" },
    buildAnother: { ar: "بناء جهاز آخر", en: "Build Another PC" },
    option:       { ar: "الخيار", en: "Option" },
    purpose:      { ar: "الغرض", en: "Purpose" },
    algorithm:    { ar: "الخوارزمية", en: "Algorithm" },
    explored:     { ar: "عدد الحالات المستكشفة", en: "Explored States" },
    totalPrice:   { ar: "السعر الكلي", en: "Total Price" },
    cpu:          { ar: "المعالج", en: "CPU" },
    motherboard:  { ar: "اللوحة الأم", en: "Motherboard" },
    ram:          { ar: "الذاكرة العشوائية", en: "RAM" },
    storage:      { ar: "التخزين", en: "Storage" },
    gpu:          { ar: "كرت الشاشة", en: "GPU" },
    psu:          { ar: "مزود الطاقة", en: "PSU" },
}

function msg(key) {
    return messages[key][currentLang];
}

async function buildPC() {
    const budgetInput = document.getElementById("budget").value;
    const purpose   = document.getElementById("purpose").value;
    const algorithm = document.getElementById("algorithm").value;

    if (!budgetInput || !purpose || !algorithm) {
        showError(msg("fillAll"));
        return;
    }

    const enteredBudget = Number(budgetInput);
    const budgetUsd = convertEnteredToUsd(enteredBudget);

    if (budgetUsd < 300) {
        showError(msg("minBudget"));
        return;
    }

    showLoading();

    try {
        const response = await fetch(`${API_URL}/build`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ budget: budgetUsd, purpose, algorithm })
        });

        const data = await response.json();
        console.log(data);

if (data.success) {
            showResults(data.builds || []);
        } else {
            if (data.min_budget !== undefined && data.min_budget !== null) {
                const convertedMinBudget = formatPrice(data.min_budget);
                if (currentLang === "ar") {
                    showError(`الحد الأدنى للميزانية هو ${convertedMinBudget}`);
                } else {
                    showError(`Minimum required budget is ${convertedMinBudget}`);
                }
            } else {
                showError(data.error || msg("noBuild"));
            }
        }

    } catch (err) {
        showError(msg("noServer"));
    }
}

function showResults(builds) {
    if (!Array.isArray(builds) || builds.length === 0) {
        showError(msg("noBuild"));
        return;
    }

    lastBuilds = builds;
    hideAll();

    const optionsContainer = document.getElementById("build-options");
    optionsContainer.innerHTML = builds
        .map((build, idx) => renderBuildOption(build, idx + 1))
        .join("");

    document.querySelector(".reset-btn span").textContent    = msg("buildAnother");
    document.getElementById("result-section").classList.remove("hidden");
}

function renderBuildOption(build, optionNumber) {
    const c = build.components;
    return `
    <div class="card build-option-card">
        <h3 class="option-title">${msg("option")} ${optionNumber}</h3>

        <div class="stats-bar">
            <div class="stat">
                <i class="fas fa-microchip stat-icon"></i>
                <span class="stat-label">${msg("algorithm")}</span>
                <span class="stat-value">${build.algorithm}</span>
            </div>
            <div class="stat">
                <i class="fas fa-project-diagram stat-icon"></i>
                <span class="stat-label">${msg("explored")}:</span>
                <span class="stat-value">${Number(build.explored_states || 0).toLocaleString()}</span>
            </div>
            <div class="stat">
                <i class="fas fa-tags stat-icon"></i>
                <span class="stat-label">${msg("totalPrice")}</span>
                <span class="stat-value">${formatPrice(build.total_price)}</span>
            </div>
        </div>

        <div class="components-grid">
            ${renderComponentCard("cpu", msg("cpu"), "fas fa-microchip", c.cpu.name, c.cpu.price)}
            ${renderComponentCard("mb", msg("motherboard"), "fas fa-server", c.motherboard.name, c.motherboard.price)}
            ${renderComponentCard("ram", msg("ram"), "fas fa-memory", c.ram.name, c.ram.price)}
            ${renderComponentCard("storage", msg("storage"), "fas fa-hdd", c.storage.name, c.storage.price)}
            ${renderComponentCard("gpu", msg("gpu"), "fas fa-tv", c.gpu.name, c.gpu.price)}
            ${renderComponentCard("psu", msg("psu"), "fas fa-plug", c.psu.name, c.psu.price)}
        </div>

        <div class="compat-badge">
            <i class="fas fa-check-circle"></i>
            <span>${msg("compatible")}</span>
        </div>
    </div>`;
}

function renderComponentCard(type, title, iconClass, name, price) {
    return `
    <div class="component-card">
        <div class="component-icon ${type}-icon">
            <i class="${iconClass}"></i>
        </div>
        <div class="component-info">
            <h4>${title}</h4>
            <p>${name}</p>
            <span class="price-tag">${formatPrice(price)}</span>
        </div>
    </div>`;
}

function showError(message) {
    hideAll();
    document.getElementById("error-msg").textContent = message;
    document.getElementById("error-box").classList.remove("hidden");
}

function showLoading() {
    hideAll();
    document.querySelector("#loading p").textContent = msg("searching");
    document.getElementById("loading").classList.remove("hidden");
    document.getElementById("build-btn").disabled = true;
}

function hideAll() {
    document.getElementById("loading").classList.add("hidden");
    document.getElementById("error-box").classList.add("hidden");
    document.getElementById("result-section").classList.add("hidden");
    document.getElementById("build-btn").disabled = false;
}

function resetForm() {
    hideAll();
    lastBuilds = [];
    document.getElementById("build-options").innerHTML = "";
    document.getElementById("budget").value    = "";
    document.getElementById("purpose").value   = "";
    document.getElementById("algorithm").value = "";
    document.getElementById("currency").value  = "OMR";
    currentCurrency = "OMR";
}

setLang("ar");

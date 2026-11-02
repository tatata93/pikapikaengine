"use strict";
(() => {
  const search = document.getElementById("search");
  const category = document.getElementById("category");
  const status = document.getElementById("search-status");
  const articles = [...document.querySelectorAll("article[data-keywords]")];
  function filter() {
    const words = search.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
    let count = 0;
    for (const article of articles) {
      const text = `${article.dataset.keywords} ${article.textContent}`.toLocaleLowerCase();
      article.hidden = !(words.every(word => text.includes(word)) &&
        (category.value === "all" || category.value === article.dataset.category));
      if (!article.hidden) count++;
    }
    status.textContent = `${count}項目 / 全${articles.length}項目。本文と図は通信なしで読めます。`;
  }
  search.addEventListener("input", filter);
  category.addEventListener("change", filter);
  window.addEventListener("hashchange", () => {
    const target = articles.find(article => `#${article.id}` === location.hash);
    if (target) { search.value = ""; category.value = "all"; filter(); target.scrollIntoView(); }
  });
})();

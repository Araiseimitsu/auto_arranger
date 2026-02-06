document.addEventListener("DOMContentLoaded", () => {
    const printButton = document.getElementById("print-button");
    if (!printButton) {
        return;
    }

    printButton.addEventListener("click", () => {
        window.print();
    });
});

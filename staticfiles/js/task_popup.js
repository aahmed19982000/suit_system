function openTaskDetails(taskId) {
    const width = 1000;
    const height = 500;
    const left = (screen.width - width) / 2;
    const top = (screen.height - height) / 2;
    const url = `/tasks/task/${taskId}/details/`;

    console.log("فتح المهمة:", url);

    window.open(
        url,
        'تفاصيل_المهمة',
        `width=${width},height=${height},top=${top},left=${left},resizable=yes,scrollbars=yes`
    );
}

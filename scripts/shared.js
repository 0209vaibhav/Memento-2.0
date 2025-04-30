// Shared functionality for loading public mementos
async function loadPublicMementosData() {
  try {
    // Load all three dataset files
    const responses = await Promise.all([
      // fetch('public-memento-markers/Dataset/mementos_culture_all_pages.json'),
      // fetch('public-memento-markers/Dataset/mementos_escapes_all_pages.json'),
      // fetch('public-memento-markers/Dataset/mementos_food_drink_all_pages.json'),
      // fetch('public-memento-markers/Dataset/mementos_things_to_do_all_pages.json'),
      // fetch('public-memento-markers/Dataset/mementos_top_news_all_pages.json'),
      fetch('public-memento-markers/Dataset/mementos_wellness_nature_all_pages.json')
    ]);

    const datasets = await Promise.all(responses.map(response => response.json()));
    const allEvents = datasets.flatMap(dataset => dataset.events || dataset);

    return allEvents;
  } catch (error) {
    console.error('Error loading public mementos data:', error);
    throw error;
  }
}

// Export the function
window.loadPublicMementosData = loadPublicMementosData; 
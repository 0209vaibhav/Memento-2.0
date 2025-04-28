// ---------------------------
// 1) Firebase references & constants
// ---------------------------
// Firebase references
// Using existing storage and db from auth.js

// Activity collection name
const ACTIVITIES_COLLECTION = 'activities';

// Activity Status Enum
const ActivityStatus = {
  DRAFT: 'draft',
  PUBLISHED: 'published',
  ARCHIVED: 'archived'
};

// Activity Visibility Enum
const ActivityVisibility = {
  PUBLIC: 'public',
  PRIVATE: 'private',
  FRIENDS: 'friends'
};

// ---------------------------
// 2) Activity validation
// ---------------------------
function validateActivity(activityData) {
  const errors = [];
  
  if (!activityData.name?.trim()) errors.push('Event name is required');
  if (!activityData.caption?.trim()) errors.push('Caption is required');
  if (!activityData.category) errors.push('Category is required');
  if (!activityData.location?.address) errors.push('Location is required');
  if (!activityData.startTime) errors.push('Start time is required');
  if (!activityData.endTime) errors.push('End time is required');

  const startDate = new Date(activityData.startTime);
  const endDate = new Date(activityData.endTime);
  if (endDate <= startDate) errors.push('End time must be after start time');

  return errors;
}

// ---------------------------
// 3) Activity CRUD operations
// ---------------------------
// Save activity to Firestore
async function saveActivity(activityData, user) {
  try {
    // Validate activity data
    const errors = validateActivity(activityData);
    if (errors.length > 0) {
      throw new Error(`Validation failed: ${errors.join(', ')}`);
    }

    // Prepare activity document with rich metadata
    const activity = {
      ...activityData,
      userId: user.uid,
      status: ActivityStatus.PUBLISHED,
      visibility: activityData.visibility || ActivityVisibility.PUBLIC,
      location: activityData.location || null,
      media: activityData.media || [],
      tags: activityData.tags || [],
      participants: activityData.participants || [],
      metadata: {
        views: 0,
        likes: 0,
        shares: 0,
        lastViewed: null
      },
      createdAt: firebase.firestore.FieldValue.serverTimestamp(),
      updatedAt: firebase.firestore.FieldValue.serverTimestamp()
    };

    // Save to Firestore
    const docRef = await db.collection(ACTIVITIES_COLLECTION).add(activity);
    return { id: docRef.id, ...activity };
  } catch (error) {
    console.error('Error saving activity:', error);
    throw error;
  }
}

// ---------------------------
// 4) Media upload
// ---------------------------
// Upload media files to Firebase Storage
async function uploadActivityMedia(files, userId) {
  try {
    const mediaUrls = [];
    
    for (const file of files) {
      // Validate file size (10MB max)
      if (file.size > 10 * 1024 * 1024) {
        throw new Error(`File ${file.name} exceeds 10MB limit`);
      }

      // Create storage reference
      const storageRef = storage.ref();
      const timestamp = Date.now();
      const fileRef = storageRef.child(`users/${userId}/activities/${timestamp}_${file.name}`);
      
      // Upload file with metadata
      const metadata = {
        contentType: file.type,
        customMetadata: {
          uploadedBy: userId,
          uploadedAt: new Date().toISOString(),
          type: 'activity-media'
        }
      };

      // Upload file
      await fileRef.put(file, metadata);
      const url = await fileRef.getDownloadURL();
      mediaUrls.push({
        url,
        type: file.type,
        name: file.name,
        size: file.size,
        timestamp: timestamp
      });
    }
    
    return mediaUrls;
  } catch (error) {
    console.error('Error uploading media:', error);
    throw error;
  }
}

// ---------------------------
// 5) Activity retrieval & filtering
// ---------------------------
// Get activities with pagination and filters
async function getActivities(filters = {}, pagination = { limit: 10, lastDoc: null }) {
  try {
    let query = db.collection(ACTIVITIES_COLLECTION)
      .where('status', '==', ActivityStatus.PUBLISHED)
      .where('visibility', '==', ActivityVisibility.PUBLIC);

    // Apply filters
    if (filters.userId) {
      query = query.where('userId', '==', filters.userId);
    }
    if (filters.category) {
      query = query.where('category', '==', filters.category);
    }
    if (filters.tags && filters.tags.length > 0) {
      query = query.where('tags', 'array-contains-any', filters.tags);
    }

    // Apply sorting
    if (filters.sortBy === 'popular') {
      query = query.orderBy('metadata.views', 'desc');
    } else {
      query = query.orderBy('createdAt', 'desc');
    }

    // Apply pagination
    if (pagination.lastDoc) {
      query = query.startAfter(pagination.lastDoc);
    }
    query = query.limit(pagination.limit);

    const snapshot = await query.get();
    
    return {
      activities: snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      })),
      lastDoc: snapshot.docs[snapshot.docs.length - 1],
      hasMore: snapshot.docs.length === pagination.limit
    };
  } catch (error) {
    console.error('Error getting activities:', error);
    throw error;
  }
}

// ---------------------------
// 6) User-specific activity management
// ---------------------------
// Get user's activities with filters
async function getUserActivities(userId, filters = {}) {
  try {
    // Check if user is authenticated
    const user = firebase.auth().currentUser;
    if (!user) {
      throw new Error('User must be logged in to access activities');
    }

    // Verify the user is accessing their own activities
    if (user.uid !== userId) {
      throw new Error('Unauthorized to access these activities');
    }

    // Ensure Firestore is initialized
    if (!db) {
      throw new Error('Database not initialized');
    }

    // Start with a basic query
    let query = db.collection(ACTIVITIES_COLLECTION)
      .where('userId', '==', userId);

    // Apply filters one at a time with error handling
    try {
      if (filters.status) {
        query = query.where('status', '==', filters.status);
      }
    } catch (error) {
      console.warn('Status filter not available yet:', error);
    }

    try {
      if (filters.category) {
        query = query.where('category', '==', filters.category);
      }
    } catch (error) {
      console.warn('Category filter not available yet:', error);
    }

    try {
      if (filters.dateRange) {
        query = query
          .where('createdAt', '>=', filters.dateRange.start)
          .where('createdAt', '<=', filters.dateRange.end);
      }
    } catch (error) {
      console.warn('Date range filter not available yet:', error);
    }

    // Apply sorting with error handling
    try {
      query = query.orderBy('createdAt', 'desc');
    } catch (error) {
      console.warn('Sorting not available yet:', error);
    }

    const snapshot = await query.get();
    return snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));
  } catch (error) {
    console.error('Error getting user activities:', error);
    if (error.code === 'failed-precondition') {
      throw new Error('Database indexes are being created. Please try again in a moment.');
    }
    throw error;
  }
}

// ---------------------------
// 7) Activity updates
// ---------------------------
// Update activity with optimistic updates
async function updateActivity(activityId, updateData, user) {
  try {
    const activityRef = db.collection(ACTIVITIES_COLLECTION).doc(activityId);
    const activity = await activityRef.get();

    if (!activity.exists) {
      throw new Error('Activity not found');
    }

    if (activity.data().userId !== user.uid) {
      throw new Error('Unauthorized to update this activity');
    }

    // Prepare update data with metadata
    const update = {
      ...updateData,
      updatedAt: firebase.firestore.FieldValue.serverTimestamp()
    };

    // If updating status, update related metadata
    if (updateData.status === ActivityStatus.PUBLISHED) {
      update['metadata.publishedAt'] = firebase.firestore.FieldValue.serverTimestamp();
    }

    await activityRef.update(update);

    return {
      id: activityId,
      ...activity.data(),
      ...update
    };
  } catch (error) {
    console.error('Error updating activity:', error);
    throw error;
  }
}

// ---------------------------
// 8) Activity interactions
// ---------------------------
// Increment activity view count
async function incrementActivityView(activityId, userId) {
  try {
    const activityRef = db.collection(ACTIVITIES_COLLECTION).doc(activityId);
    
    await activityRef.update({
      'metadata.views': firebase.firestore.FieldValue.increment(1),
      'metadata.lastViewed': firebase.firestore.FieldValue.serverTimestamp(),
      [`metadata.viewedBy.${userId}`]: firebase.firestore.FieldValue.serverTimestamp()
    });
  } catch (error) {
    console.error('Error incrementing activity view:', error);
    throw error;
  }
}

// Toggle activity like
async function toggleActivityLike(activityId, userId) {
  try {
    const activityRef = db.collection(ACTIVITIES_COLLECTION).doc(activityId);
    const activity = await activityRef.get();

    if (!activity.exists) {
      throw new Error('Activity not found');
    }

    const likes = activity.data().metadata?.likes || 0;
    const likedBy = activity.data().metadata?.likedBy || {};
    
    if (likedBy[userId]) {
      // Unlike
      await activityRef.update({
        'metadata.likes': firebase.firestore.FieldValue.increment(-1),
        [`metadata.likedBy.${userId}`]: firebase.firestore.FieldValue.delete()
      });
      return false;
    } else {
      // Like
      await activityRef.update({
        'metadata.likes': firebase.firestore.FieldValue.increment(1),
        [`metadata.likedBy.${userId}`]: firebase.firestore.FieldValue.serverTimestamp()
      });
      return true;
    }
  } catch (error) {
    console.error('Error toggling activity like:', error);
    throw error;
  }
}

// ---------------------------
// 9) Activity lifecycle management
// ---------------------------
// Delete activity
async function deleteActivity(activityId, user) {
  try {
    if (!user || !user.uid) {
      throw new Error('User must be logged in to delete activities');
    }

    const activityRef = db.collection(ACTIVITIES_COLLECTION).doc(activityId);
    const activity = await activityRef.get();

    if (!activity.exists) {
      throw new Error('Activity not found');
    }

    if (activity.data().userId !== user.uid) {
      throw new Error('Unauthorized to delete this activity');
    }

    // Delete associated media files
    const mediaFiles = activity.data().media || [];
    for (const media of mediaFiles) {
      if (typeof media === 'string') {
        // Handle case where media is a direct URL string
        const fileRef = storage.refFromURL(media);
        await fileRef.delete();
      } else if (media.url) {
        // Handle case where media is an object with url property
        const fileRef = storage.refFromURL(media.url);
        await fileRef.delete();
      }
    }

    // Delete activity document
    await activityRef.delete();
  } catch (error) {
    console.error('Error deleting activity:', error);
    throw error;
  }
}

// Archive activity
async function archiveActivity(activityId, user) {
  return updateActivity(activityId, { status: ActivityStatus.ARCHIVED }, user);
}

// Save activity as draft
async function saveActivityDraft(activityData, user) {
  const draftData = {
    ...activityData,
    status: ActivityStatus.DRAFT
  };
  return saveActivity(draftData, user);
}

// ---------------------------
// 10) Module exports
// ---------------------------
// Export functions
window.Activities = {
  save: saveActivity,
  uploadMedia: uploadActivityMedia,
  getActivities,
  getUserActivities,
  update: updateActivity,
  delete: deleteActivity,
  archive: archiveActivity,
  saveDraft: saveActivityDraft,
  validate: validateActivity
}; 
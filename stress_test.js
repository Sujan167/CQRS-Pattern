import http from "k6/http";
import { sleep, check } from "k6";
import { uuidv4 } from "https://jslib.k6.io/k6-utils/1.4.0/index.js";

export let options = {
	stages: [
		{ duration: "20s", target: 10 }, // ramp-up
		{ duration: "40s", target: 50 }, // sustain load
		{ duration: "20s", target: 0 }, // ramp-down
	],
};

export default function () {
	// Generate unique ID for title
	let uniqueID = uuidv4();

	// 1. POST - Create task
	let createRes = http.post(
		"http://localhost:8000/v1/tasks",
		JSON.stringify({
			title: `Task ${uniqueID}`,
			description: `This is task created during stress test with id ${uniqueID}`,
		}),
		{
			headers: { "Content-Type": "application/json" },
		}
	);

	check(createRes, {
		"POST status is 201": (r) => r.status === 201,
	});

	let taskId;
	try {
		taskId = JSON.parse(createRes.body).id;
	} catch (e) {
		console.error("Failed to parse ID from POST response:", createRes.body);
		return;
	}

	// 2. GET - Fetch all tasks
	let getAllRes = http.get("http://localhost:8000/v1/tasks");
	check(getAllRes, {
		"GET all tasks status is 200": (r) => r.status === 200,
	});

	// 3. GET - Fetch single task by ID
	let getOneRes = http.get(`http://localhost:8000/v1/tasks/${taskId}`);
	check(getOneRes, {
		"GET one task status is 200": (r) => r.status === 200,
	});

	// 4. PUT - Update task
	let updateRes = http.put(
		`http://localhost:8000/v1/tasks/${taskId}`,
		JSON.stringify({
			is_completed: true,
			title: `Updated Task ${uniqueID}`,
			description: `Updated description for task ${uniqueID}`,
		}),
		{
			headers: { "Content-Type": "application/json" },
		}
	);

	check(updateRes, {
		"PUT update task status is 200": (r) => r.status === 200,
	});

	// 5. DELETE - Remove task
	let deleteRes = http.del(`http://localhost:8000/v1/tasks/${taskId}`);
	check(deleteRes, {
		"DELETE task status is 200 or 204": (r) => r.status === 200 || r.status === 204,
	});

	sleep(1); // simulate think time
}

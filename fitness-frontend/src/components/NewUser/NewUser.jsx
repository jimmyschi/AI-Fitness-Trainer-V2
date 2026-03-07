import { useState, useEffect } from "react";
import { useNavigate } from 'react-router-dom';
import './NewUser.css'
const NewUser = () => {
    const [user, setUser] = useState(null);
    const [username, setUsername] = useState("");
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [name, setName] = useState("");
    const [weight, setWeight] = useState(0.0);
    const [gender, setGender] = useState("");
    const [isValid, setIsValid] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        if(user) {
            console.log(`User created on frontend ${user}`);
            navigate("/FitnessApp");
        }
    }, [user]);

    function validatePassword(password) {
        const regex = /^(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$/; // Ensure at least 8 characters and 1 special character
        return regex.test(password);
    };

    const handleNewUser = async (event) => {
        event.preventDefault();
        console.log("Edited handleNewUser function called!");

        if(!validatePassword(password)) {
            alert("Password must be at least 8 characters long and contain at least one special character.");
            return;
        }
        //TODO: Add new user to the backend
        try {
            const formData = new FormData();
            formData.append('username', username);
            formData.append('email', email);
            formData.append('password', password);
            formData.append('name', name);
            formData.append('weight', weight);
            formData.append('gender', gender);
            console.log(`process.env.REACT_APP_API_URL: ${process.env.REACT_APP_API_URL}`);
            const response = await fetch(`${process.env.REACT_APP_API_URL}/api/new/`, {
                method: 'POST',
                body: formData,
            })
            if(!response.ok) {
                setUser(false);
                throw new Error(`HTTP error! status ${response.status}`);
            } else {
                setUser(true);
            }
            const userResponse = await response.json();
            if(!userResponse) {
                throw new Error("No user returned from the backend.");
            }
            console.log(`userResponse: {userResponse}`);
            localStorage.setItem('token', userResponse.token);
            localStorage.setItem('user_id', userResponse.user_id);
            
            // setUser(userResponse.exists);
        } catch(error) {
            console.error("Error creating new user:", error);
        }
    };

    return (
        <div className="newuser-container">
            <h1 className="newuser-title">Create New User Below</h1>
            <form className="newuser-form" onSubmit={handleNewUser}>
                <label>Username: <input className="username-input" type="text" onChange={(e) => setUsername(e.target.value)} required/></label>
                <label>Email: <input className="email-input" type="email" onChange={(e) => setEmail(e.target.value)} required/></label>
                <label>Password: <input className="password-input" type="password" value={password} onChange={(e) => {
                    setPassword(e.target.value);
                    setIsValid(validatePassword(e.target.value));
                }} required/></label>
                <label>Name: <input className="name-input" type="text" onChange={(e) => setName(e.target.value)} required/></label>
                <label>Weight: <input className="weight-input" type="number" onChange={(e) => setWeight(e.target.value)} required/></label>
                <label>Gender:<select className="gender-input" id="gender" value={gender} onChange={(e) => setGender(e.target.value)}>
                    <option value=""></option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                </select></label>
                <button className="submit-button" type="submit">Create New User</button>
            </form>
        </div>
    )
};

export default NewUser;
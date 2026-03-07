import {Routes, Route} from 'react-router-dom';
import UserLogin from '../UserLogin/UserLogin';
import NewUser from '../NewUser/NewUser';
import FitnessApp from '../FitnessApp/FitnessApp';

function App() {
    return (
        <div className="App">
            <Routes>
                <Route path="/" element={<UserLogin />} />
                <Route path="/NewUser" element={<NewUser />} />
                <Route path="/FitnessApp" element={<FitnessApp />} />
            </Routes>
        </div>
    );   
}

export default App;